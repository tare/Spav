#!/usr/bin/env python

import os
import sys

import argparse

import bokeh.io
import bokeh.layouts
import bokeh.models

import spav

import argparse

import logging

parser = argparse.ArgumentParser(description='Spav')
parser.add_argument('--array',action='store_true',dest='array',required=False,
                    help='show the array view')
parser.add_argument('--arrays',action='store_true',dest='arrays',required=False,
                    help='show the arrays view')
parser.add_argument('--common-coordinate',action='store_true',dest='common_coordinate',required=False,
                    help='show the common coordinate view')
parser.add_argument('--aar-coefficients',action='store_true',dest='aar_coefficients',required=False,
                    help='show the aar coefficient view')
parser.add_argument('--level-coefficients',action='store_true',dest='level_coefficients',required=False,
                    help='show the level coefficient view')
parser.add_argument('-v','--version',action='version',version='%s %s'%(parser.prog,'0.0.1'))

parser.set_defaults(arrays=False)
parser.set_defaults(array=False)
parser.set_defaults(common_coordinate=False)
parser.set_defaults(aar_coefficients=False)
parser.set_defaults(level_coefficients=False)

options = parser.parse_args()

tab_list = []

data_filename = os.path.join(os.path.dirname(__file__),'data/data.hdf5')
static_directory = os.path.join(os.path.basename(os.path.dirname(__file__)),'static')

if options.arrays:
  view = spav.ExpressionOnArrays(data_filename,static_directory)
  tab_list.append(bokeh.models.widgets.Panel(child=view.layout,title='Expression on arrays'))

if options.array:
  view = spav.ExpressionOnArray(data_filename,static_directory)
  tab_list.append(bokeh.models.widgets.Panel(child=view.layout,title='Expression on array'))

if options.common_coordinate:
  view = spav.ExpressionInCommonCoordinate(data_filename)
  tab_list.append(bokeh.models.widgets.Panel(child=view.layout,title='Expression in common coordinate'))

if options.level_coefficients:
  view = spav.LevelExpressionCoefficients(data_filename)
  tab_list.append(bokeh.models.widgets.Panel(child=view.layout,title='Expression coefficients per variable'))

if options.aar_coefficients:
  view = spav.AARExpressionCoefficients(data_filename)
  tab_list.append(bokeh.models.widgets.Panel(child=view.layout,title='Expression coefficients per AAR'))

if len(tab_list) > 0:
  bokeh.core.validation.silence(bokeh.core.validation.warnings.MISSING_RENDERERS,True)
  bokeh.io.curdoc().add_root(bokeh.models.widgets.Tabs(tabs=tab_list))
  bokeh.io.curdoc().title = 'Spav'
else:
  logging.warning('No views were specified!')
  sys.exit(0)
