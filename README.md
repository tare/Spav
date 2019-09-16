# Spav
A tool for visualizing [Splotch](https://github.com/tare/Splotch) results.

## Overview
Spav currently supports five different interactive views for visualizing and exploring Splotch results.

A custom version of Spav is used on [https://als-st.nygenome.org](https://als-st.nygenome.org).

### Expression on arrays
This view visualizes expression estimates on all the arrays simultaneously.
![Arrays view](images/arrays.png)

### Expression on array
This view visualizes expression estimates on the selected array.
The user can filter arrays based on the level 1 information (see [Splotch](https://github.com/tare/Splotch)).
![Array view](images/array.png)

### Expression in common coordinate
This view visualizes expression estimates in common coordinate system.
The expression estimates are separated based on the level 1 information.
![Common coordinate view](images/common_coordinate.png)

### Expression coefficients per level 1 variable
This view visualizes expression coefficients across level 1 variables per AAR.
![Coefficients per level 1 variable view](images/coeffiecients_level.png)

### Expression coefficients per anatomical annotation region (AAR)
This view visualizes expression coefficients across AARs per level 1 variable.
![Coefficients per AAR](images/coeffiecients_aar.png)

## Usage

### Installation
Spav has been tested on Python 3.7.

The required packages can be installed as follows
```console
$ pip install -r requirements.txt
```

### Data preparation
The script ``spav_prepare_data.py`` can be used for preparing the Splotch results to be used with Spav
```console
$ python spav_prepare_data.py --help
usage: spav_prepare_data.py [-h] -d DATA_DIRECTORY -o OUTPUT_DIRECTORY -s
                            SERVER_DIRECTORY [-c] [-v]

A script for preparing Splotch results for Span

optional arguments:
  -h, --help            show this help message and exit
  -d DATA_DIRECTORY, --data-directory DATA_DIRECTORY
                        data directory
  -o OUTPUT_DIRECTORY, --output-directory OUTPUT_DIRECTORY
                        output directory
  -s SERVER_DIRECTORY, --server-directory SERVER_DIRECTORY
                        server directory
  -c, --no-copy         create symbolic links instead of copying images
  -v, --version         show program's version number and exit
```

For instance, you can run the following command
```console
$ python spav_prepare_data.py -d $DATA_DIRECTORY -o $OUTPUT_DIRECTORY -s $SPAV_DIRECTORY
```
This command will create the directories ``$SPAV_DIRECTORY/static`` and ``$SPAV_DIRECTORY/data``.
The directory ``$SPAV_DIRECTORY/static`` contains symbolic links pointing to the bright-field images and the ``$SPAV_DIRECTORY/data.hdf5`` file contains the estimates.

### Deployment

#### Standalone Bokeh server
The script ``main.py`` implements our Bokeh application
```console
$ python main.py --help
usage: main.py [-h] [--arrays] [--array] [--common-coordinate]
               [--aar-coefficients] [--level-coefficients] [-v]

Spav

optional arguments:
  -h, --help            show this help message and exit
  --arrays              show the array view
  --array               show the arrays view
  --common-coordinate   show the common coordinate view
  --aar-coefficients    show the aar coefficient view
  --level-coefficients  show the level coefficient view
  -v, --version         show program's version number and exit
```

To fire up the Bokeh application with all the implemented views you can execute the following command
```console
$ bokeh serve $SPAV_DIRECTORY --show --args --arrays --array --common-coordinate --aar-coefficients --level-coefficients
```

#### Embedding the Bokeh server inside a Jupyter notebook
Please see [Notebook.ipynb](Notebook.ipynb).
