# Spav
A tool for visualizing Splotch results

## Usage

The script ``spav_prepare_data.py`` can be used for preparing the Splotch results to be used with Spav
```console
$ python spav_prepare_data.py --help
usage: spav_prepare_data.py [-h] -d DATA_DIRECTORY -o OUTPUT_DIRECTORY -s
                            SERVER_DIRECTORY [-v]

A script for preparing Splotch results for Span

optional arguments:
  -h, --help            show this help message and exit
  -d DATA_DIRECTORY, --data-directory DATA_DIRECTORY
                        data directory
  -o OUTPUT_DIRECTORY, --output-directory OUTPUT_DIRECTORY
                        output directory
  -s SERVER_DIRECTORY, --server-directory SERVER_DIRECTORY
                        server directory
  -v, --version         show program's version number and exit
```

For instance, you can run the following command
```console
$ python spav_prepare_data.py -d $DATA_DIRECTORY -o $OUTPUT_DIRECTORY -s $SPAV_DIRECTORY
```

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
