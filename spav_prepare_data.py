#!/usr/bin/env python

import os
import sys
import shutil
import re
import glob
import pickle
import pathlib
import argparse

import pandas as pd
import numpy
import h5py
import scipy.stats

import logging

from PIL import Image
Image.MAX_IMAGE_PIXELS = 1000000000

from splotch.utils import (read_stan_csv, read_array_metadata,
                           to_stan_variables, registration,
                           read_aar_matrix)

def escape_h5py_object_name(name,escape_characters=['/']):
  for escape_character in escape_characters:
    name = name.replace(escape_character,' ')
  return name

def generate_data_files(data_directory,output_directory,server_directory,copy):
  # unpickle data_directory/information.p
  sample_information = pickle.load(open(os.path.normpath('%s/information.p'%(data_directory)),'rb')) 
  # .. and extract useful variables
  genes = sample_information['genes'] # read genes
  metadata = sample_information['metadata'] # read metadata table
  n_levels = sample_information['n_levels'] # read the number of levels
  aar_names = sample_information['annotation_mapping'] # read the aar names
  scaling_factor = sample_information['scaling_factor'] # read the scaling factor
  beta_mapping = sample_information['beta_mapping'] # read the names of the beta variables

  # get the names of the sample files
  sample_files = glob.glob(os.path.normpath('%s/*/combined_*.csv'%(output_directory)))
  # read the posterior samples of beta_level_1 and log_lambda
  variable_names = ['log_lambda','beta_level_1']
  samples = {genes[int(re.search('combined_([0-9]*)\.csv$',sample_file).group(1))-1]: read_stan_csv(sample_file,
      variable_names) for sample_file in sample_files}

  # calculate the posterior means of lambda, i.e. exp(log_lambda)
  lambda_posterior_means = pd.DataFrame.from_dict({key: numpy.exp(samples[key]['log_lambda']).mean(0) for key in samples},
          orient='index',
          columns=pd.MultiIndex.from_tuples(
              sample_information['filenames_and_coordinates'],
              names=['file','coordinate']))

  pathlib.Path(os.path.normpath('%s/data'%(server_directory))).mkdir(parents=True,exist_ok=True)
  pathlib.Path(os.path.normpath('%s/static'%(server_directory))).mkdir(parents=True,exist_ok=True)

  count_files = numpy.array(list(lambda_posterior_means.columns.levels[0]))
  registered_coordinates_dict,_,_ = registration(count_files,metadata)

  with h5py.File(os.path.normpath('%s/data/data.hdf5'%(server_directory)),'w') as f:

    density_evaluation_points = numpy.linspace(-10,10,500)

    beta_grp = f.create_group('beta')
    beta_grp.create_dataset('density_evaluation_points',data=density_evaluation_points)
    beta_grp.create_dataset('aar_names',data=numpy.string_(aar_names))
    beta_grp.create_dataset('beta_variables',data=numpy.string_(beta_mapping['beta_level_1']))
    density_beta_grp = beta_grp.create_group('density')
    for gene in samples.keys():
      gene_beta_grp = beta_grp.create_group(gene)
      tmp = numpy.zeros((len(density_evaluation_points),len(beta_mapping['beta_level_1']),len(aar_names)))
      for aar_idx,aar_variable in enumerate(aar_names):
        for beta_idx,beta_variable in enumerate(beta_mapping['beta_level_1']):
          tmp[:,beta_idx,aar_idx] = scipy.stats.gaussian_kde(samples[gene]['beta_level_1'][:,beta_idx,aar_idx]).evaluate(density_evaluation_points)
      density_beta_grp.create_dataset(gene,data=tmp)
 
    for level_1 in beta_mapping['beta_level_1']:
      f.create_group('level_1/%s'%(escape_h5py_object_name(level_1)))

    f.create_dataset('genes',data=numpy.string_(list(lambda_posterior_means.index)))
    arrays_grp = f.create_group('arrays')

    files_per_level = {}
  
    for count_file in count_files:
      array_grp = arrays_grp.create_group(escape_h5py_object_name(os.path.basename(count_file)))
      image_array_grp = array_grp.create_group('image')
      data_array_grp = array_grp.create_group('data')
      metadata_array_grp = array_grp.create_group('metadata')
  
      image_filename = metadata[metadata['Count file'] == count_file]['Image file'].values[0]

      if not os.path.exists(os.path.normpath('%s/static/%s'%(server_directory,os.path.basename(image_filename)))):

        if copy:
          shutil.copy(os.path.normpath('%s/%s'%(os.getcwd(),image_filename)),os.path.normpath('%s/static/%s'%(server_directory,os.path.basename(image_filename))))
        else:
          os.symlink(os.path.normpath('%s/%s'%(os.getcwd(),image_filename)),os.path.normpath('%s/static/%s'%(server_directory,os.path.basename(image_filename))))
      else:
        logging.warning('%s was not overwritten!'%(os.path.normpath('%s/static/%s'%(server_directory,os.path.basename(image_filename)))))

      levels = list(map(str,read_array_metadata(metadata,count_file,n_levels)))
  
      image_array_grp.create_dataset('filename',data=os.path.basename(image_filename))
      tissue_image = Image.open(image_filename)
      image_array_grp.create_dataset('resolution',data=tissue_image.size)
      image_array_grp.create_dataset('spot_radius',data=0.5*100.0e-6*tissue_image.size[0]/6.2e-3)
      image_array_grp.create_dataset('title',data='%s (%s)'%(' '.join(levels),os.path.basename(image_filename)))
  
      xdim,ydim = tissue_image.size
      pixel_dim = 194.0/(6200.0/xdim)
  
      coordinates = numpy.array([list(map(float,coordinate.split('_')))
                                 for coordinate in list(lambda_posterior_means[count_file].columns)])

      registered_coordinates = numpy.array([list(map(float,registered_coordinates_dict[count_file][coordinate].split('_'))) for coordinate in list(lambda_posterior_means[count_file].columns)])
  
      pixel_coordinates = pixel_dim*(coordinates-1)
      pixel_coordinates[:,1] = ydim-pixel_coordinates[:,1]
  
      annotation_filename = metadata[metadata['Count file'] == count_file]['Annotation file'].values[0]
      array_aar_matrix,array_aar_names = read_aar_matrix(annotation_filename)
      array_aar_matrix = array_aar_matrix[lambda_posterior_means[count_file].columns]
  
      annotations = [array_aar_names[numpy.where(spot)[0][0]] for spot in array_aar_matrix.values.T]
  
      data_array_grp.create_dataset('coordinates',data=pixel_coordinates)
      data_array_grp.create_dataset('registered_coordinates',data=registered_coordinates)
      data_array_grp.create_dataset('annotations',data=numpy.string_(annotations))
      expressions_data_array_grp = data_array_grp.create_group('expressions')
      for index,row in lambda_posterior_means[count_file].iterrows():
        expressions_data_array_grp.create_dataset(escape_h5py_object_name(index),data=row.values)

      metadata_array_grp.create_dataset('levels',data=numpy.string_(levels))

      if levels[0] not in files_per_level:
          files_per_level[levels[0]] = []
      files_per_level[levels[0]].append(os.path.basename(count_file))

    for key in files_per_level:
      f['level_1/%s'%(key)].create_dataset('files',data=numpy.string_(files_per_level[key]))

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='A script for preparing Splotch results for Span')
  parser.add_argument('-d','--data-directory',action='store',
                      dest='data_directory',type=str,required=True,
                      help='data directory')
  parser.add_argument('-o','--output-directory',action='store',
                      dest='output_directory',type=str,required=True,
                      help='output directory')
  parser.add_argument('-s','--server-directory',action='store',
                      dest='server_directory',type=str,required=True,
                      help='server directory')
  parser.add_argument('-c','--no-copy',action='store_false',dest='copy',required=False,
                      help='create symbolic links instead of copying images')
  parser.add_argument('-v','--version',action='version',
                      version='%s %s'%(parser.prog,'0.0.1'))

  parser.set_defaults(copy=True)
  options = parser.parse_args()

  generate_data_files(options.data_directory,options.output_directory,options.server_directory,options.copy)

  sys.exit(0)
