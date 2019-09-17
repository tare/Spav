import os

import numpy
import colorsys

import h5py
import bokeh.models
import bokeh.plotting

from bokeh.core.properties import List, String
from bokeh.util.compiler import TypeScript
from bokeh.models import TextInput

class AutocompleteInputCustom(TextInput):
    __implementation__ = TypeScript("""
      import {TextInput, TextInputView} from "models/widgets/text_input"
      
      import {empty, display, undisplay, div, Keys} from "core/dom"
      import * as p from "core/properties"
      import {clamp} from "core/util/math"
      
      export class AutocompleteInputViewCustom extends TextInputView {
        model: AutocompleteInputCustom
      
        protected _open: boolean = false
      
        protected _last_value: string = ""
      
        protected _hover_index: number = 0
      
        protected menu: HTMLElement
      
        render(): void {
          super.render()
      
          this.input_el.classList.add("bk-autocomplete-input")
      
          this.input_el.addEventListener("keydown", (event) => this._keydown(event))
          this.input_el.addEventListener("keyup", (event) => this._keyup(event))
      
          this.menu = div({class: ["bk-menu", "bk-below"]})
          this.menu.addEventListener("click", (event) => this._menu_click(event))
          this.menu.addEventListener("mouseover", (event) => this._menu_hover(event))
          this.el.appendChild(this.menu)
          undisplay(this.menu)
        }
      
        change_input(): void {
          if (this._open && this.menu.children.length > 0) {
            this.model.value = this.menu.children[this._hover_index].textContent!
            this.input_el.focus()
            this._hide_menu()
          } else {
            this.model.value = this.input_el.value
            this.input_el.focus()
            this._hide_menu()
          }
        }
      
        protected _update_completions(completions: string[]): void {
          empty(this.menu)
      
          for (const text of completions) {
            const item = div({}, text)
            this.menu.appendChild(item)
          }
          if (completions.length > 0)
            this.menu.children[0].classList.add('bk-active')
      
        }
      
        protected _show_menu(): void {
          if (!this._open) {
            this._open = true
            this._hover_index = 0
            this._last_value = this.model.value
            display(this.menu)
      
            const listener = (event: MouseEvent) => {
              const {target} = event
              if (target instanceof HTMLElement && !this.el.contains(target)) {
                document.removeEventListener("click", listener)
                this._hide_menu()
              }
            }
            document.addEventListener("click", listener)
          }
        }
      
        protected _hide_menu(): void {
          if (this._open) {
            this._open = false
            undisplay(this.menu)
          }
        }
      
        protected _menu_click(event: MouseEvent): void {
          if (event.target != event.currentTarget && event.target instanceof Element) {
            this.model.value = event.target.textContent!
            this.input_el.focus()
            this._hide_menu()
          }
        }
      
        protected _menu_hover(event: MouseEvent): void {
          if (event.target != event.currentTarget && event.target instanceof Element) {
            let i = 0
            for (i = 0; i<this.menu.children.length; i++) {
              if (this.menu.children[i].textContent! == event.target.textContent!)
                break
            }
            this._bump_hover(i)
          }
        }
      
        protected _bump_hover(new_index: number): void {
          const n_children = this.menu.children.length
          if (this._open && n_children > 0) {
            this.menu.children[this._hover_index].classList.remove('bk-active')
            this._hover_index = clamp(new_index, 0, n_children-1)
            this.menu.children[this._hover_index].classList.add('bk-active')
          }
        }
      
        _keydown(_event: KeyboardEvent): void {}
      
        _keyup(event: KeyboardEvent): void {
          switch (event.keyCode) {
            case Keys.Enter: {
              this.change_input()
              break
            }
            case Keys.Esc: {
              this._hide_menu()
              break
            }
            case Keys.Up: {
              this._bump_hover(this._hover_index-1)
              break
            }
            case Keys.Down: {
              this._bump_hover(this._hover_index+1)
              break
            }
            default: {
              const value = this.input_el.value
      
              if (value.length <= 1) {
                this._hide_menu()
                return
              }
      
              const completions: string[] = []
              for (const text of this.model.completions) {
                if (text.indexOf(value) != -1)
                  completions.push(text)
              }
      
              this._update_completions(completions)
      
              if (completions.length == 0)
                this._hide_menu()
              else
                this._show_menu()
            }
          }
        }
      }
      
      export namespace AutocompleteInputCustom {
        export type Attrs = p.AttrsOf<Props>
      
        export type Props = TextInput.Props & {
          completions: p.Property<string[]>
        }
      }
      
      export interface AutocompleteInputCustom extends AutocompleteInputCustom.Attrs {}
      
      export class AutocompleteInputCustom extends TextInput {
        properties: AutocompleteInputCustom.Props
      
        constructor(attrs?: Partial<AutocompleteInputCustom.Attrs>) {
          super(attrs)
        }
      
        static initClass(): void {
          this.prototype.type = "AutocompleteInputCustom"
          this.prototype.default_view = AutocompleteInputViewCustom
      
          this.define<AutocompleteInputCustom.Props>({
            completions: [ p.Array, [] ],
          })
        }
      }
      AutocompleteInputCustom.initClass()

    """)
    completions = List(String,help="")

class ExpressionOnArrays:
  def __init__(self,data_filename,static_directory,gene=None,n_columns=4):
    self.filename = data_filename
    self.static_directory = static_directory
    self.genes = self.__read_genes()
    self.data = self.__read_array_data()

    self.n_columns = n_columns

    if gene is None:
      self.gene = self.genes[0]
    else:
      self.gene = gene

    self.source_spots,self.vmin,self.vmax = self.__create_source_spots(self.gene)

    self.source_image = self.__create_source_image()

    self.color_mapper = bokeh.models.mappers.LinearColorMapper('Viridis256',low=self.vmin,high=self.vmax)
    self.ticker = bokeh.models.BasicTicker(base=2,mantissas=[1,5])

    self.textinput_gene = AutocompleteInputCustom(value=self.gene,title='Gene:',completions=self.genes,width=300)
    self.textinput_gene.on_change('value',self.__update_plot)

    self.error_pretext = bokeh.models.widgets.Div(text='',width=125,height=20)

    self.__plots = self.__plot()

    self.layout = bokeh.layouts.layout([bokeh.layouts.layout(self.__plots[0:2]),bokeh.layouts.gridplot(self.__plots[2:-1],merge_tools=True,toolbar_location='left',toolbar_options=dict(logo=None),sizing_mode='scale_both'),bokeh.layouts.layout(self.__plots[-1])],sizing_mode='scale_both')

  def __read_genes(self):
    with h5py.File(self.filename,'r') as f:
        genes = list(map(lambda x: x.decode('UTF-8'),list(f['genes'])))

    return genes

  def __read_array_data(self):
    data = {}
    with h5py.File(self.filename,'r') as f:
      for array in f['arrays']:
        data[array] = {'coordinates': numpy.array(f['arrays'][array]['data']['coordinates']),
                       'annotations': list(map(lambda x: x.decode('UTF-8'),numpy.array(f['arrays'][array]['data']['annotations']))),
                       'spot_radius': float(numpy.array(f['arrays'][array]['image']['spot_radius'])),
                       'resolution': numpy.array(f['arrays'][array]['image']['resolution']),
                       'title': f['arrays'][array]['image']['title'][()]}

    return data

  def __create_source_spots(self,gene):
    expression_data = {}
    with h5py.File(self.filename,'r') as f:
      for array in f['arrays']:
        expression_data[array] = {'expressions': numpy.array(f['arrays'][array]['data']['expressions'][gene])}

    vmin = 0
    vmax = numpy.percentile(numpy.hstack([expression_data[key]['expressions'] for key in expression_data]),95)
  
    source_spots = []
    for key in self.data:
      source_spots.append(bokeh.models.ColumnDataSource({'x': self.data[key]['coordinates'][:,0],
                                                         'y': self.data[key]['coordinates'][:,1],
                                                         'expression': expression_data[key]['expressions'],
                                                         'annotation': self.data[key]['annotations'],
                                                         'spot_radius': self.data[key]['coordinates'].shape[0]*[self.data[key]['spot_radius']]}))

    return source_spots, vmin, vmax

  def __create_source_image(self):
    source_image = []
    with h5py.File(self.filename,'r') as f:
      for array in f['arrays']:
        source_image.append(bokeh.models.ColumnDataSource({'image': [os.path.join(self.static_directory,f['arrays'][array]['image']['filename'][()])]}))
    return source_image

  def __update_plot(self,attr,old,new):
    if new not in self.genes:
      self.error_pretext.text = '<b>Gene not found!</b>'
      return
    self.gene = new
    self.error_pretext.text = ''
    self.error_pretext.text = '<b>Please wait.</b>'
    self.textinput_gene.disabled = True

    source_spots,vmin,vmax = self.__create_source_spots(self.gene)

    for n in range(0,len(source_spots)):
      self.source_spots[n].data = source_spots[n].data

    self.color_mapper.low = vmin
    self.color_mapper.high = vmax

    self.error_pretext.text = ''
    self.textinput_gene.disabled = False

  def __plot(self):
    plots = []
  
    plots.append([self.textinput_gene])
    plots.append([self.error_pretext])
  
    subplots = []
    for n,key in enumerate(self.data.keys()):

      if n > 0 and n%self.n_columns == 0:
        plots.append(subplots)
        subplots = []
      
      s = bokeh.plotting.figure(x_range=(0,self.data[key]['resolution'][0]),
                                y_range=(0,self.data[key]['resolution'][1]),
                                match_aspect=True,aspect_scale=1,
                                tools=[bokeh.models.tools.PanTool(),bokeh.models.tools.WheelZoomTool(),bokeh.models.tools.ResetTool()])
      s.add_layout(bokeh.models.Title(text=self.data[key]['title']),'above')
      s.toolbar.logo = None
      s.toolbar_location = None
      s.axis.visible = False

      s.image_url(url='image',x=0,y=0,anchor='bottom_left',
                  w=self.data[key]['resolution'][0],h=self.data[key]['resolution'][1],
                  source=self.source_image[n])
    
      spots = s.scatter(x='x',y='y',radius='spot_radius',
                        fill_color={'field': 'expression','transform': self.color_mapper},
                        fill_alpha=0.8,line_color=None,source=self.source_spots[n])

      hover = bokeh.models.HoverTool(tooltips=[('Expression','@expression'),('Annotation','@annotation')],renderers=[spots])

      s.add_tools(hover)

      subplots.append(s)

    if len(subplots) > 0:
      plots.append(subplots)
    
    s = bokeh.plotting.figure(width=235,plot_height=100,title=None,x_axis_location=None,y_axis_location=None,
                              tools='pan,wheel_zoom,reset',min_border=0,outline_line_color=None)
    colorbar = bokeh.models.ColorBar(color_mapper=self.color_mapper,ticker=self.ticker,
                                     label_standoff=6,border_line_color=None,location=(0,0),
                                     major_tick_line_color='black',title='Expression (λ)',orientation='horizontal')
    s.add_layout(colorbar,'above')
    s.toolbar.logo = None
    s.toolbar_location = None
    
    plots.append([s])
    
    return plots

class ExpressionOnArray:
  def __init__(self,data_filename,static_directory,gene=None):
    self.filename = data_filename
    self.static_directory = static_directory
    self.genes = self.__read_genes()
    self.variables,self.arrays = self.__read_data()
    self.data = self.__read_array_data()

    if gene is None:
      self.gene = self.genes[0]
    else:
      self.gene = gene

    self.variable = self.variables[0]
    self.array = self.arrays[self.variable][0]

    self.source_array,self.vmin,self.vmax = self.__create_source_spots(self.gene,self.array)
    self.source_image = self.__create_source_image(self.array)

    self.color_mapper = bokeh.models.mappers.LinearColorMapper('Viridis256',low=self.vmin,high=self.vmax)
    self.ticker = bokeh.models.BasicTicker(base=2,mantissas=[1,5])

    self.error_pretext = bokeh.models.widgets.Div(text='',width=125,height=20)

    self.textinput_gene = AutocompleteInputCustom(value=self.gene,title='Gene:',completions=self.genes,width=300)
    self.textinput_gene.on_change('value',self.__update_plot_gene)

    self.select_variable = bokeh.models.widgets.Select(value=self.variable,options=self.variables,title='Level 1:',width=100)
    self.select_variable.on_change('value',self.__update_plot_variable)

    self.select_array = bokeh.models.widgets.Select(value=self.array,options=self.arrays[self.variable],title='Array:',width=100)
    self.select_array.on_change('value',self.__update_plot_array)

    self.__plots = self.__plot()

    self.layout = bokeh.layouts.layout([bokeh.layouts.layout(self.__plots[0:3]),bokeh.layouts.layout(self.__plots[3:-1],sizing_mode='scale_height'),bokeh.layouts.layout(self.__plots[-1])],sizing_mode='scale_width')

  def __read_genes(self):
    with h5py.File(self.filename,'r') as f:
        genes = list(map(lambda x: x.decode('UTF-8'),list(f['genes'])))

    return genes

  def __read_array_data(self):
    data = {}
    with h5py.File(self.filename,'r') as f:
      for array in f['arrays']:
        data[array] = {'coordinates': numpy.array(f['arrays'][array]['data']['coordinates']),
                       'annotations': list(map(lambda x: x.decode('UTF-8'),numpy.array(f['arrays'][array]['data']['annotations']))),
                       'spot_radius': float(numpy.array(f['arrays'][array]['image']['spot_radius'])),
                       'resolution': numpy.array(f['arrays'][array]['image']['resolution']),
                       'title': f['arrays'][array]['image']['title'][()]}

    return data

  def __read_data(self,key='level_1'):
    arrays = {}

    with h5py.File(self.filename,'r') as f:
      variables = list(f[key].keys())

      for variable in variables:
        arrays[variable] = list(map(lambda x: x.decode('UTF-8'),list(f['%s/%s'%(key,variable)]['files'])))

    return variables,arrays

  def __create_source_image(self,array):
    with h5py.File(self.filename,'r') as f:
      source_image = bokeh.models.ColumnDataSource({'image': [os.path.join(self.static_directory,f['arrays'][array]['image']['filename'][()])],
                                                    'xdim': [list(f['arrays'][array]['image']['resolution'])[0]],
                                                    'ydim': [list(f['arrays'][array]['image']['resolution'])[1]]})
    return source_image

  def __create_source_spots(self,gene,array):
    expression_data = {}
    with h5py.File(self.filename,'r') as f:
      for key in f['arrays']:
        expression_data[key] = {'expressions': numpy.array(f['arrays'][key]['data']['expressions'][gene])}

    vmin = 0
    vmax = numpy.percentile(numpy.hstack([expression_data[key]['expressions'] for key in expression_data]),95)

    expression_data = expression_data[array]
  
    source_spots = bokeh.models.ColumnDataSource({'x': self.data[array]['coordinates'][:,0],
                                                  'y': self.data[array]['coordinates'][:,1],
                                                  'expression': expression_data['expressions'],
                                                  'annotation': self.data[array]['annotations'],
                                                  'spot_radius': self.data[array]['coordinates'].shape[0]*[self.data[array]['spot_radius']]})

    return source_spots, vmin, vmax

  def __update_plot_gene(self,attr,old,new):
    if new not in self.genes:
      self.error_pretext.text = '<b>Gene not found!</b>'
      return
    self.gene = new
    self.error_pretext.text = ''

    self.textinput_gene.disabled = True
    self.error_pretext.text = '<b>Please wait.</b>'

    source_array,self.vmin,self.vmax = self.__create_source_spots(self.gene,self.array)

    self.source_array.data = source_array.data

    self.color_mapper.low = self.vmin
    self.color_mapper.high = self.vmax

    self.textinput_gene.disabled = False
    self.error_pretext.text = ''

  def __update_plot_variable(self,attr,old,new):
    self.variable = new

    self.array = self.arrays[self.variable][0]

    self.select_array.options = self.arrays[self.variable]
    self.select_array.value = self.array

  def __update_plot_array(self,attr,old,new):
    self.array = new

    source_image = self.__create_source_image(self.array)
    source_array,_,_ = self.__create_source_spots(self.gene,self.array)

    self.source_array.data = source_array.data
    self.source_image.data = source_image.data

    self.s.x_range.start = 0
    self.s.x_range.end = source_image.data['xdim'][0]
    self.s.y_range.start = 0
    self.s.y_range.end = source_image.data['ydim'][0]

  def __plot(self):
    plots = []
  
    plots.append([self.textinput_gene])
    plots.append([self.error_pretext])
    plots.append([self.select_variable,self.select_array])
  
    self.s = bokeh.plotting.figure(x_range=(0,self.data[self.array]['resolution'][0]),
                                   y_range=(0,self.data[self.array]['resolution'][1]),
                                   match_aspect=True,aspect_scale=1,
                                   tools=[bokeh.models.tools.PanTool(),bokeh.models.tools.WheelZoomTool(),bokeh.models.tools.ResetTool(),bokeh.models.tools.SaveTool()])

    self.s.toolbar.logo = None
    self.s.toolbar_location = 'left'
    self.s.axis.visible = False
    
    self.s.image_url(url='image',x=0,y=0,anchor='bottom_left',w='xdim',h='ydim',source=self.source_image)
    
    spots = self.s.scatter(x='x',y='y',radius='spot_radius',
                           fill_color={'field': 'expression','transform': self.color_mapper},
                           fill_alpha=0.8,line_color=None,source=self.source_array)

    hover = bokeh.models.HoverTool(tooltips=[('Expression','@expression'),('Annotation','@annotation')],renderers=[spots])

    self.s.add_tools(hover)

    plots.append([self.s])
    
    s = bokeh.plotting.figure(width=235,plot_height=100,
                              title=None,x_axis_location=None,y_axis_location=None,
                              tools='pan,wheel_zoom,reset',min_border=0,outline_line_color=None)
    colorbar = bokeh.models.ColorBar(color_mapper=self.color_mapper,
                                     ticker=self.ticker,label_standoff=6,
                                     border_line_color=None,location=(0,0),major_tick_line_color='black',
                                     title='Expression (λ)',orientation='horizontal')
    s.add_layout(colorbar,'above')
    s.toolbar.logo = None
    s.toolbar_location = None

    plots.append([s])

    return plots

class ExpressionInCommonCoordinate:
  def __init__(self,data_filename,gene=None,n_columns=4):
    self.filename = data_filename
    self.genes = self.__read_genes()
    self.variables,self.arrays = self.__read_data()
    self.data = self.__read_array_data()

    self.n_columns = n_columns

    if gene is None:
      self.gene = self.genes[0]
    else:
      self.gene = gene

    self.source_spots,self.vmin,self.vmax = self.__create_source_spots(self.gene)

    self.color_mapper = bokeh.models.mappers.LinearColorMapper('Inferno256',low=self.vmin,high=self.vmax)
    self.ticker = bokeh.models.BasicTicker(base=2,mantissas=[1,5])

    self.error_pretext = bokeh.models.widgets.Div(text='',width=125,height=20)

    self.textinput_gene = AutocompleteInputCustom(value=self.gene,title='Gene:',completions=self.genes,width=300)
    self.textinput_gene.on_change('value',self.__update_plot_gene)

    self.slider = bokeh.models.Slider(start=0.01,end=1,value=0.1,step=0.005,title='Spot radius')
    self.slider.on_change('value',self.__update_spot_size)

    self.s = []
    for variable in self.variables:
      s = bokeh.plotting.figure(x_range=(-8,8),
                                y_range=(-8,8),
                                match_aspect=True,aspect_scale=1,
                                tools=[bokeh.models.tools.PanTool(),bokeh.models.tools.WheelZoomTool(),bokeh.models.tools.ResetTool(),bokeh.models.tools.SaveTool()])
      s.add_layout(bokeh.models.Title(text=variable),'above') 
      s.xgrid.visible = False
      s.ygrid.visible = False
      s.background_fill_color = 'gray'
      s.toolbar.logo = None
      s.toolbar_location = None
      s.axis.visible = False

      self.s.append(s)

    self.__plots = self.__plot()

    self.layout = bokeh.layouts.layout([bokeh.layouts.layout(self.__plots[0:3]),bokeh.layouts.gridplot(self.__plots[3:-1],merge_tools=True,toolbar_location='left',toolbar_options=dict(logo=None),sizing_mode='scale_both'),bokeh.layouts.layout(self.__plots[-1])],sizing_mode='scale_both')

  def __read_genes(self):
    with h5py.File(self.filename,'r') as f:
        genes = list(map(lambda x: x.decode('UTF-8'),list(f['genes'])))

    return genes

  def __read_array_data(self):
    data = {}
    with h5py.File(self.filename,'r') as f:
      for array in f['arrays']:
        data[array] = {'coordinates': numpy.array(f['arrays'][array]['data']['registered_coordinates']),
                       'annotations': list(map(lambda x: x.decode('UTF-8'),numpy.array(f['arrays'][array]['data']['annotations'])))}

    return data

  def __read_data(self,key='level_1'):
    arrays = {}

    with h5py.File(self.filename,'r') as f:
      variables = list(f[key].keys())

      for variable in variables:
        arrays[variable] = list(map(lambda x: x.decode('UTF-8'),list(f['%s/%s'%(key,variable)]['files'])))

    return variables,arrays

  def __create_source_spots(self,gene):
    expression_data = {}
    with h5py.File(self.filename,'r') as f:
      for key in f['arrays']:
        expression_data[key] = numpy.array(f['arrays'][key]['data']['expressions'][gene])

    source_spots = []

    for variable in self.variables:
      tmp_coordinates = []
      tmp_expressions = []
      tmp_annotations = []
      for array in self.arrays[variable]:
        tmp_coordinates.append(self.data[array]['coordinates'])
        tmp_expressions.append(expression_data[array])
        tmp_annotations.append(self.data[array]['annotations'])

      source_spots.append(bokeh.models.ColumnDataSource({'x': numpy.vstack(tmp_coordinates)[:,0],
                                                         'y': numpy.vstack(tmp_coordinates)[:,1],
                                                         'expression': numpy.concatenate(tmp_expressions),
                                                         'annotation': numpy.concatenate(tmp_annotations)}))

    vmin = 0
    vmax = numpy.percentile(numpy.hstack([expression_data[key] for key in expression_data]),95)

    return source_spots, vmin, vmax

  def __update_plot_gene(self,attr,old,new):
    if new not in self.genes:
      self.error_pretext.text = '<b>Gene not found!</b>'
      return
    self.gene = new
    self.error_pretext.text = ''

    self.textinput_gene.disabled = True
    self.error_pretext.text = '<b>Please wait.</b>'

    source_spots,self.vmin,self.vmax = self.__create_source_spots(self.gene)

    for idx in range(0,len(source_spots)):
      self.source_spots[idx].data = source_spots[idx].data

    self.color_mapper.low = self.vmin
    self.color_mapper.high = self.vmax

    self.textinput_gene.disabled = False
    self.error_pretext.text = ''

  def __update_spot_size(self,attr,old,new):
    for spots_idx in range(0,len(self.spots)):
      self.spots[spots_idx].glyph.radius = float(new)

  def __plot(self):
    plots = []
  
    plots.append([self.textinput_gene])
    plots.append([self.error_pretext])
    plots.append([self.slider])

    subplots = []
    self.spots = []
    for n,key in enumerate(self.variables):

      if n > 0 and n%self.n_columns == 0:
        plots.append(subplots)
        subplots = []
  
      
      spots = self.s[n].scatter(x='x',y='y',radius=self.slider.value,
                                fill_color={'field': 'expression','transform': self.color_mapper},
                                fill_alpha=0.8,line_color=None,source=self.source_spots[n])
  
      hover = bokeh.models.HoverTool(tooltips=[('Expression','@expression'),('Annotation','@annotation')],renderers=[spots])
      self.s[n].add_tools(hover)

      self.spots.append(spots)

      subplots.append(self.s[n])
  
    if len(subplots) > 0:
      plots.append(subplots)
    
    s = bokeh.plotting.figure(width=235,plot_height=100,
                              title=None,x_axis_location=None,y_axis_location=None,
                              tools='pan,wheel_zoom,reset',min_border=0,outline_line_color=None)
    colorbar = bokeh.models.ColorBar(color_mapper=self.color_mapper,
                                     ticker=self.ticker,label_standoff=6,
                                     border_line_color=None,location=(0,0),major_tick_line_color='black',
                                     title='Expression (λ)',orientation='horizontal')
    s.add_layout(colorbar,'above')
    s.toolbar.logo = None
    s.toolbar_location = None

    plots.append([s])

    return plots

class AARExpressionCoefficients:
  def __init__(self,data_filename,gene=None,n_columns=4,height=250):
    self.filename = data_filename 
    self.genes = self.__read_genes()
    self.evaluation_points,self.variables,self.aars = self.__read_data()

    self.n_columns = n_columns
    self.height = height

    if gene is None:
      self.gene = self.genes[0]
    else:
      self.gene = gene

    self.source,max_value = self.__create_source(self.gene)

    self.textinput_gene = AutocompleteInputCustom(value=self.gene,title='Gene:',completions=self.genes,width=300)
    self.textinput_gene.on_change('value',self.__update_plot)
    self.error_pretext = bokeh.models.widgets.Div(text='',width=125,height=20)

    self.rangeslider_limits = bokeh.models.widgets.RangeSlider(start=self.evaluation_points.min(),end=self.evaluation_points.max(),step=0.25,
                                                               value=(self.evaluation_points.min(),self.evaluation_points.max()),title='X-axis range',width=300)
    self.rangeslider_limits.on_change('value',self.__update_xaxislimits)

    self.s = []
    for variable in self.variables:
      # TODO: https://github.com/bokeh/bokeh/issues/9182
      #s = bokeh.plotting.figure(x_range=(self.evaluation_points.min(),self.evaluation_points.max()),y_range=(0,max_value),title=variable,tools=[bokeh.models.HoverTool(tooltips=[('AAR', '@label')])],y_axis_label='Posterior probability density',x_axis_label='Coefficient, β')
      s = bokeh.plotting.figure(plot_height=self.height,x_range=(self.evaluation_points.min(),self.evaluation_points.max()),y_range=(0,max_value),title=variable,tools='',y_axis_label='Posterior probability density',x_axis_label='Coefficient, β')

      s.grid.grid_line_alpha = 0.2
      s.xgrid.visible = True
      s.ygrid.visible = False
      s.xgrid.grid_line_color = 'black'

      self.s.append(s)

    self.__plots = self.__plot()

    self.layout = bokeh.layouts.layout([bokeh.layouts.layout(self.__plots[0:3]),bokeh.layouts.gridplot(self.__plots[3:],merge_tools=True,toolbar_location='left',toolbar_options=dict(logo=None),sizing_mode='stretch_width')],sizing_mode='stretch_width')

  def __read_genes(self):
    with h5py.File(self.filename,'r') as f:
      genes = list(map(lambda x: x.decode('UTF-8'),list(f['genes'])))

    return genes

  def __read_data(self):
    with h5py.File(self.filename,'r') as f:
      density_evaluation_points = numpy.array(f['beta']['density_evaluation_points'])
      variables = list(map(lambda x: x.decode('UTF-8'),list(f['beta']['beta_variables'])))
      aar_names = list(map(lambda x: x.decode('UTF-8'),list(f['beta']['aar_names'])))
    return density_evaluation_points,variables,aar_names

  def __create_source(self,gene):
    source = {}
    for variable in self.variables:
      source[variable] = {}
      for aar in self.aars:
        source[variable][aar] = bokeh.models.ColumnDataSource({'x': self.evaluation_points,'label':len(self.evaluation_points)*[aar]})

    with h5py.File(self.filename,'r') as f:
      tmp = numpy.array(f['beta']['density'][gene])

    max_value = numpy.max(tmp)*1.2

    for variable_idx,variable in enumerate(self.variables):
      for aar_idx,aar in enumerate(self.aars):
        source[variable][aar].add(numpy.zeros(tmp.shape[0]),'y1')
        source[variable][aar].add(tmp[:,variable_idx,aar_idx],'y2')

    return source,max_value

  def __update_plot(self,attr,old,new):
    if new not in self.genes:
      self.error_pretext.text = '<b>Gene not found!</b>'
      return
    self.gene = new
    self.error_pretext.text = ''

    self.error_pretext.text = '<b>Please wait.</b>'
    self.textinput_gene.disabled = True

    source,max_value = self.__create_source(self.gene)

    for variable_idx,variable in enumerate(self.variables):
      for aar in self.aars:
        self.source[variable][aar].data = source[variable][aar].data
      self.s[variable_idx].y_range.start = 0
      self.s[variable_idx].y_range.end = max_value

    self.textinput_gene.disabled = False
    self.error_pretext.text = ''

  def __update_xaxislimits(self,attr,old,new):
    for variable_idx in range(0,len(self.variables)):
      self.s[variable_idx].x_range.start = new[0]
      self.s[variable_idx].x_range.end = new[1]

  def __plot(self):
    hsv = [(x*1.0/len(self.aars),0.5,0.5) for x in range(len(self.aars))]
    palette = list(map(lambda x: colorsys.hsv_to_rgb(*x),hsv))
    palette = [tuple(round(j*255) for j in i) for i in palette]

    plots = []

    plots.append([self.textinput_gene])
    plots.append([self.error_pretext])
    plots.append([self.rangeslider_limits])

    subplots = []
    for variable_idx,variable in enumerate(self.variables):
      if variable_idx > 0 and variable_idx%self.n_columns == 0:
        plots.append(subplots)
        subplots = []
      for aar_idx,aar in enumerate(self.aars):
        self.s[variable_idx].varea('x','y1','y2',fill_color=palette[aar_idx],alpha=0.4,source=self.source[variable][aar],legend=aar)
        self.s[variable_idx].legend.click_policy='hide'

        # TODO: make sure this generalizes
        height = min(numpy.floor((self.height)/(2*len(self.aars))).astype(int),15)

        self.s[variable_idx].legend.label_text_font_size = '%dpx'%(height*0.8)
        self.s[variable_idx].legend.glyph_height = height
        self.s[variable_idx].legend.glyph_width = height
        self.s[variable_idx].legend.spacing = 1
        self.s[variable_idx].legend.padding = 1
        self.s[variable_idx].legend.margin = 5
        self.s[variable_idx].legend.label_height = height

      subplots.append(self.s[variable_idx])
    
    if len(subplots) > 0:
      plots.append(subplots)
  
    return plots

class LevelExpressionCoefficients:
  def __init__(self,data_filename,gene=None,n_columns=4,height=250):
    self.filename = data_filename 
    self.genes = self.__read_genes()
    self.evaluation_points,self.variables,self.aars = self.__read_data()

    self.n_columns = n_columns
    self.height = height

    if gene is None:
      self.gene = self.genes[0]
    else:
      self.gene = gene

    self.source,max_value = self.__create_source(self.gene)

    self.textinput_gene = AutocompleteInputCustom(value=self.gene,title='Gene:',completions=self.genes,width=300)
    self.textinput_gene.on_change('value',self.__update_plot)
    self.error_pretext = bokeh.models.widgets.Div(text='',width=125,height=20)

    self.rangeslider_limits = bokeh.models.widgets.RangeSlider(start=self.evaluation_points.min(),end=self.evaluation_points.max(),step=0.25,
                                                               value=(self.evaluation_points.min(),self.evaluation_points.max()),title='X-axis range',width=300)
    self.rangeslider_limits.on_change('value',self.__update_xaxislimits)

    self.s = []
    for aar in self.aars:
      # TODO: https://github.com/bokeh/bokeh/issues/9182
      #s = bokeh.plotting.figure(x_range=(self.evaluation_points.min(),self.evaluation_points.max()),y_range=(0,max_value),title=variable,tools=[bokeh.models.HoverTool(tooltips=[('AAR', '@label')])],y_axis_label='Posterior probability density',x_axis_label='Coefficient, β')
      s = bokeh.plotting.figure(plot_height=self.height,x_range=(self.evaluation_points.min(),self.evaluation_points.max()),y_range=(0,max_value),title=aar,tools='',y_axis_label='Posterior probability density',x_axis_label='Coefficient, β')

      s.grid.grid_line_alpha = 0.2
      s.xgrid.visible = True
      s.ygrid.visible = False
      s.xgrid.grid_line_color = 'black'

      self.s.append(s)

    self.__plots = self.__plot()

    self.layout = bokeh.layouts.layout([bokeh.layouts.layout(self.__plots[0:3]),bokeh.layouts.gridplot(self.__plots[3:],merge_tools=True,toolbar_location='left',toolbar_options=dict(logo=None),sizing_mode='stretch_width')],sizing_mode='stretch_width')

  def __read_genes(self):
    with h5py.File(self.filename,'r') as f:
      genes = list(map(lambda x: x.decode('UTF-8'),list(f['genes'])))

    return genes

  def __read_data(self):
    with h5py.File(self.filename,'r') as f:
      density_evaluation_points = numpy.array(f['beta']['density_evaluation_points'])
      variables = list(map(lambda x: x.decode('UTF-8'),list(f['beta']['beta_variables'])))
      aar_names = list(map(lambda x: x.decode('UTF-8'),list(f['beta']['aar_names'])))
    return density_evaluation_points,variables,aar_names

  def __create_source(self,gene):
    source = {}
    for variable in self.variables:
      source[variable] = {}
      for aar in self.aars:
        source[variable][aar] = bokeh.models.ColumnDataSource({'x': self.evaluation_points,'label':len(self.evaluation_points)*[variable]})

    with h5py.File(self.filename,'r') as f:
      tmp = numpy.array(f['beta']['density'][gene])

    max_value = numpy.max(tmp)*1.2

    for variable_idx,variable in enumerate(self.variables):
      for aar_idx,aar in enumerate(self.aars):
        source[variable][aar].add(numpy.zeros(tmp.shape[0]),'y1')
        source[variable][aar].add(tmp[:,variable_idx,aar_idx],'y2')

    return source,max_value

  def __update_plot(self,attr,old,new):
    if new not in self.genes:
      self.error_pretext.text = '<b>Gene not found!</b>'
      return
    self.gene = new
    self.error_pretext.text = ''

    self.error_pretext.text = '<b>Please wait.</b>'
    self.textinput_gene.disabled = True

    source,max_value = self.__create_source(self.gene)

    for aar_idx,aar in enumerate(self.aars):
      for variable in self.variables:
        self.source[variable][aar].data = source[variable][aar].data
      self.s[aar_idx].y_range.start = 0
      self.s[aar_idx].y_range.end = max_value

    self.textinput_gene.disabled = False
    self.error_pretext.text = ''

  def __update_xaxislimits(self,attr,old,new):
    for aar_idx in range(0,len(self.aars)):
      self.s[aar_idx].x_range.start = new[0]
      self.s[aar_idx].x_range.end = new[1]

  def __plot(self):
    hsv = [(x*1.0/len(self.variables),0.5,0.5) for x in range(len(self.variables))]
    palette = list(map(lambda x: colorsys.hsv_to_rgb(*x),hsv))
    palette = [tuple(round(j*255) for j in i) for i in palette]

    plots = []

    plots.append([self.textinput_gene])
    plots.append([self.error_pretext])
    plots.append([self.rangeslider_limits])

    subplots = []
    for aar_idx,aar in enumerate(self.aars):
      if aar_idx > 0 and aar_idx%self.n_columns == 0:
        plots.append(subplots)
        subplots = []
      for variable_idx,variable in enumerate(self.variables):
        self.s[aar_idx].varea('x','y1','y2',fill_color=palette[variable_idx],alpha=0.4,source=self.source[variable][aar],legend=variable)
        self.s[aar_idx].legend.click_policy='hide'

        # TODO: make sure this generalizes
        height = min(numpy.floor((self.height)/(2*len(self.variables))).astype(int),15)

        self.s[aar_idx].legend.label_text_font_size = '%dpx'%(height*0.8)
        self.s[aar_idx].legend.glyph_height = height
        self.s[aar_idx].legend.glyph_width = height
        self.s[aar_idx].legend.spacing = 1
        self.s[aar_idx].legend.padding = 1
        self.s[aar_idx].legend.margin = 5
        self.s[aar_idx].legend.label_height = height

      subplots.append(self.s[aar_idx])
    
    if len(subplots) > 0:
      plots.append(subplots)
  
    return plots
