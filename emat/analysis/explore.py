

import pandas
import numpy
from ..viz import colors
from .. import styles
from plotly import graph_objs as go
import ipywidgets as widget
from math import isclose
from ..scope.parameter import IntegerParameter, CategoricalParameter, BooleanParameter
from typing import Mapping
import warnings
import scipy.stats
from ..scope.box import Box

class Explore:

	def __init__(self, scope, data, box=None):
		self.scope = scope
		self.data = data
		if box is None:
			box = Box('explore', scope=scope)
		self.box = box
		self._categorical_data = {}
		self._base_histogram = {}
		self._figures_hist = {}
		self._figures_freq = {}
		self._figures_kde = {}
		self._slider_widgets = {}
		self._base_kde = {}
		self._two_way = {}
		self._status_txt = widget.HTML(
			value="<i>Explore Status Not Set</i>",
		)
		self._status_pie = go.FigureWidget(
			go.Pie(
				values=[75, 250],
				labels=['Inside', 'Outside'],
				hoverinfo='label+value',
				textinfo='percent',
				textfont_size=10,
				marker=dict(
					colors=[
						colors.DEFAULT_HIGHLIGHT_COLOR,
						colors.DEFAULT_BASE_COLOR,
					],
					line=dict(color='#FFF', width=0.25),
				)
			),
			layout=dict(
				width=100,
				height=100,
				showlegend=False,
				margin=dict(l=10, r=10, t=10, b=10),
			)
		)
		self._status = widget.HBox(
			[self._status_txt, self._status_pie],
			layout=dict(
				justify_content = 'space-between',
				align_items = 'center',
			)
		)
		self._update_status()

	def status(self):
		return self._status

	def _update_status(self, selection=None):
		if selection is None:
			selection = self.box.inside(self.data)
		text = '<span style="font-weight:bold;font-size:150%">{:,d} Cases Selected out of {:,d} Total Cases</span>'
		values = (int(numpy.sum(selection)), int(selection.size))
		self._status_txt.value = text.format(*values)
		self._status_pie.data[0].values = [values[0], values[1]-values[0]]

	def _compute_histogram(self, col, selection, bins=None):
		if col not in self._base_histogram:
			if bins is None:
				bins = 20
			bar_heights, bar_x = numpy.histogram(self.data[col], bins=bins)
			self._base_histogram[col] = bar_heights, bar_x
		else:
			bar_heights, bar_x = self._base_histogram[col]
		bins_left = bar_x[:-1]
		bins_width = bar_x[1:] - bar_x[:-1]
		bar_heights_select, bar_x = numpy.histogram(self.data[col][selection], bins=bar_x)
		return bar_heights, bar_heights_select, bins_left, bins_width

	def _compute_frequencies(self, col, selection, labels):
		if col in self._categorical_data:
			v = self._categorical_data[col]
		else:
			self._categorical_data[col] = v = self.data[col].astype(
				pandas.CategoricalDtype(categories=labels, ordered=False)
			).cat.codes
		if col not in self._base_histogram:
			bar_heights, bar_x = numpy.histogram(v, bins=numpy.arange(0, len(labels) + 1))
			self._base_histogram[col] = bar_heights, bar_x
		else:
			bar_heights, bar_x = self._base_histogram[col]
		bar_heights_select, _ = numpy.histogram(v[selection], bins=numpy.arange(0, len(labels) + 1))
		return bar_heights, bar_heights_select, labels

	def _compute_kde(self, col, selection, bw_method=None):
		if col not in self._base_kde:
			kernel_base = scipy.stats.gaussian_kde(self.data[col], bw_method=bw_method)
			common_bw = kernel_base.covariance_factor()
			range_ = (self.data[col].min(), self.data[col].max())
			x_points = numpy.linspace(*range_, 250)
			y_base = kernel_base(x_points)
			self._base_kde[col] = kernel_base, common_bw, x_points, y_base
		else:
			kernel_base, common_bw, x_points, y_base = self._base_kde[col]

		kernel_select = scipy.stats.gaussian_kde(self.data[col][selection], bw_method=common_bw)
		y_select = kernel_select(x_points)
		return x_points, y_base, y_select

	def _update_histogram_figure(self, col, *, selection=None):
		if col in self._figures_hist:
			fig = self._figures_hist[col]
			bins = fig._bins
			if selection is None:
				selection = self.box.inside(self.data)
			bar_heights, bar_heights_select, bins_left, bins_width = self._compute_histogram(col, selection, bins=bins)
			with fig.batch_update():
				fig.data[0].y = bar_heights_select
				fig.data[1].y = bar_heights - bar_heights_select

	def _update_frequencies_figure(self, col, *, selection=None):
		if col in self._figures_freq:
			fig = self._figures_freq[col]
			labels = fig._labels
			if selection is None:
				selection = self.box.inside(self.data)
			bar_heights, bar_heights_select, labels = self._compute_frequencies(col, selection, labels=labels)
			with fig.batch_update():
				fig.data[0].y = bar_heights_select
				fig.data[1].y = bar_heights - bar_heights_select

	def _update_kde_figure(self, col, *, selection=None):
		if col in self._figures_kde:
			fig = self._figures_kde[col]
			if selection is None:
				selection = self.box.inside(self.data)
			x_points, y_base, y_select = self._compute_kde(col, selection)
			with fig.batch_update():
				fig.data[1].y = y_select

	def _update_all_figures(self, *, selection=None):
		if selection is None:
			selection = self.box.inside(self.data)
		self._update_status(selection=selection)
		for col in self._figures_hist:
			self._update_histogram_figure(col, selection=selection)
		for col in self._figures_freq:
			self._update_frequencies_figure(col, selection=selection)
		for col in self._figures_kde:
			self._update_kde_figure(col, selection=selection)
		for key in self._two_way:
			self._two_way[key]._on_box_change(selection=selection)

	def _create_histogram_figure(self, col, bins=20, *, selection=None):
		if col in self._figures_hist:
			self._update_histogram_figure(col, selection=selection)
		else:
			if selection is None:
				selection = self.box.inside(self.data)
			bar_heights, bar_heights_select, bins_left, bins_width = self._compute_histogram(
				col, selection, bins=bins
			)
			fig = go.FigureWidget(
				data=[
					go.Bar(
						x=bins_left,
						y=bar_heights_select,
						width=bins_width,
						name='Inside',
						marker_color=colors.DEFAULT_HIGHLIGHT_COLOR,
					),
					go.Bar(
						x=bins_left,
						y=bar_heights - bar_heights_select,
						width=bins_width,
						name='Outside',
						marker_color=colors.DEFAULT_BASE_COLOR,
					),
				],
				layout=dict(
					barmode='stack',
					showlegend=False,
					margin=dict(l=10, r=10, t=10, b=10),
					**styles.figure_dims,
				),
			)
			fig._bins = bins
			fig._figure_kind = 'histogram'
			self._figures_hist[col] = fig

	def _create_frequencies_figure(self, col, labels=None, *, selection=None):
		if col in self._figures_freq:
			self._update_frequencies_figure(col)
		else:
			if selection is None:
				selection = self.box.inside(self.data)
			bar_heights, bar_heights_select, labels = self._compute_frequencies(col, selection, labels=labels)
			fig = go.FigureWidget(
				data=[
					go.Bar(
						x=labels,
						y=bar_heights_select,
						name='Inside',
						marker_color=colors.DEFAULT_HIGHLIGHT_COLOR,
					),
					go.Bar(
						x=labels,
						y=bar_heights - bar_heights_select,
						name='Outside',
						marker_color=colors.DEFAULT_BASE_COLOR,
					),
				],
				layout=dict(
					barmode='stack',
					showlegend=False,
					margin=dict(l=10, r=10, t=10, b=10),
					width=250,
					height=150,
				),
			)
			fig._labels = labels
			fig._figure_kind = 'frequency'
			self._figures_freq[col] = fig

	def _create_kde_figure(self, col, bw_method=None, *, selection=None):
		if col in self._figures_kde:
			self._update_kde_figure(col, selection=selection)
		else:
			if selection is None:
				selection = self.box.inside(self.data)
			x_points, y_base, y_select = self._compute_kde(
				col, selection, bw_method
			)
			fig = go.FigureWidget(
				data=[
					go.Scatter(
						x=x_points,
						y=y_base,
						name='Inside',
						fill='tozeroy',
						marker_color=colors.DEFAULT_BASE_COLOR,
					),
					go.Scatter(
						x=x_points,
						y=y_select,
						name='Outside',
						fill='tozeroy',  #fill='tonexty',
						marker_color=colors.DEFAULT_HIGHLIGHT_COLOR,
					),
				],
				layout=dict(
					showlegend=False,
					margin=dict(l=10, r=10, t=10, b=10),
					**styles.figure_dims,
				),
			)
			fig._figure_kind = 'kde'
			self._figures_kde[col] = fig

	def get_histogram_figure(self, col, bins=20):
		try:
			this_type = self.scope.get_dtype(col)
		except:
			this_type = 'float'
		if this_type in ('cat','bool'):
			return self.get_frequency_figure(col)
		self._create_histogram_figure(col, bins=bins)
		return self._figures_hist[col]

	def get_frequency_figure(self, col):
		if self.scope.get_dtype(col) == 'cat':
			labels = self.scope.get_cat_values(col)
		else:
			labels = [False, True]
		self._create_frequencies_figure(col, labels=labels)
		return self._figures_freq[col]

	def get_kde_figure(self, col):
		self._create_kde_figure(col)
		return self._figures_kde[col]


	def _make_range_widget(
			self,
			i,
			min_value=None,
			max_value=None,
			readout_format=None,
			integer=False,
			steps=100,
	):
		"""Construct a RangeSlider to manipulate a Box threshold."""

		current_setting = self.box.get(i, (None, None))

		# Use current setting as min and max if still unknown
		if current_setting[0] is not None and min_value is None:
			min_value = current_setting[0]
		if current_setting[1] is not None and max_value is None:
			max_value = current_setting[1]

		if min_value is None:
			raise ValueError("min_value cannot be None if there is no current setting")
		if max_value is None:
			raise ValueError("max_value cannot be None if there is no current setting")

		close_to_max_value = max_value - 0.0051*(max_value-min_value)
		close_to_min_value = min_value + 0.0051 * (max_value - min_value)

		current_min = min_value if current_setting[0] is None else current_setting[0]
		current_max = max_value if current_setting[1] is None else current_setting[1]

		slider_type = widget.IntRangeSlider if integer else widget.FloatRangeSlider

		controller = slider_type(
			value=[current_min, current_max],
			min=min_value,
			max=max_value,
			step=((max_value - min_value) / steps) if not integer else 1,
			disabled=False,
			continuous_update=False,
			orientation='horizontal',
			readout=True,
			readout_format=readout_format,
			description='',
			style=styles.slider_style,
			layout=styles.slider_layout,
		)

		def on_value_change(change):
			new_setting = change['new']
			if new_setting[0] <= close_to_min_value:
				new_setting = (None, new_setting[1])
			if new_setting[1] >= close_to_max_value:
				new_setting = (new_setting[0], None)
			self.box.set_bounds(i, *new_setting)
			self._update_all_figures()

		controller.observe(on_value_change, names='value')

		return controller

	def _make_togglebutton_widget(
			self,
			i,
			cats=None,
			*,
			df=None,
	):
		"""Construct a MultiToggleButtons to manipulate a Box categorical set."""

		if cats is None and df is not None:
			if isinstance(df[i].dtype, pandas.CategoricalDtype):
				cats = df[i].cat.categories

		current_setting = self.box.get(i, set())

		from ..interactive.multitoggle import MultiToggleButtons
		controller = MultiToggleButtons(
			description='',
			style=styles.slider_style,
			options=list(cats),
			disabled=False,
			button_style='',  # 'success', 'info', 'warning', 'danger' or ''
			layout=styles.togglebuttons_layout,
		)
		controller.values = current_setting

		def on_value_change(change):
			new_setting = change['new']
			self.box.replace_allowed_set(i, new_setting)
			self._update_all_figures()

		controller.observe(on_value_change, names='value')

		return controller


	def get_widget(
			self,
			i,
			min_value=None,
			max_value=None,
			readout_format=None,
			steps=200,
			*,
			df=None,
			histogram=None,
			tall=True,
			with_selector=True,
			style='hist',
	):
		"""Get a control widget for a Box threshold."""

		if self.scope is None:
			raise ValueError('cannot get_widget with no scope')

		if with_selector and i not in self._slider_widgets:
			# Extract min and max from scope if not given explicitly
			if i not in self.scope.get_measure_names():
				if min_value is None:
					min_value = self.scope[i].min
				if max_value is None:
					max_value = self.scope[i].max

			# Extract min and max from `df` if still missing (i.e. for Measures)
			if df is not None:
				if min_value is None:
					min_value = df[i].min()
				if max_value is None:
					max_value = df[i].max()

			# Extract min and max from `_viz_data` if still missing
			if min_value is None:
				min_value = self.data[i].min()
			if max_value is None:
				max_value = self.data[i].max()

			if isinstance(self.scope[i], BooleanParameter):
				self._slider_widgets[i] = self._make_togglebutton_widget(
					i,
					cats=[False, True],
				)
			elif isinstance(self.scope[i], CategoricalParameter):
				cats = self.scope.get_cat_values(i)
				self._slider_widgets[i] = self._make_togglebutton_widget(
					i,
					cats=cats,
				)
			elif isinstance(self.scope[i], IntegerParameter):
				readout_format = readout_format or 'd'
				self._slider_widgets[i] = self._make_range_widget(
					i,
					min_value=min_value,
					max_value=max_value,
					readout_format=readout_format,
					integer=True,
					steps=steps,
				)
			else:
				readout_format = readout_format or '.3g'
				self._slider_widgets[i] = self._make_range_widget(
					i,
					min_value=min_value,
					max_value=max_value,
					readout_format=readout_format,
					integer=False,
					steps=steps,
				)

		if style == 'kde':
			fig = self.get_kde_figure(i)
		else:
			if not isinstance(histogram, Mapping):
				histogram = {}
			fig = self.get_histogram_figure(i, **histogram)

		stack = [
			widget.Label(i),
			fig
		]
		if with_selector:
			stack.append(self._slider_widgets[i])
		return widget.VBox(
			stack,
			layout=styles.widget_frame,
		)



	def _get_widgets(self, *include, with_selector=True, style='hist'):

		if self.scope is None:
			raise ValueError('cannot create visualization with no scope')

		viz_widgets = []
		for i in include:
			if i not in self.scope:
				warnings.warn(f'{i} not in scope')
			elif i not in self.data.columns:
				warnings.warn(f'{i} not in data')
			else:
				viz_widgets.append(self.get_widget(i, with_selector=with_selector, style=style))

		return widget.Box(viz_widgets, layout=widget.Layout(flex_flow='row wrap'))

	def selectors(self, *include, style='hist'):
		if len(include) == 1 and isinstance(include, (tuple,list)):
			include = include[0]
		return self._get_widgets(*include, with_selector=True, style=style)

	def viewers(self, *include, style='kde'):
		if len(include) == 1 and isinstance(include, (tuple,list)):
			include = include[0]
		if len(include) == 0:
			include = self.scope.get_measure_names()
		return self._get_widgets(*include, with_selector=False, style=style)

	def uncertainty_selectors(self, style='hist'):
		return self.selectors(*self.scope.get_uncertainty_names(), style=style)

	def uncertainty_viewers(self, style='kde'):
		return self.viewers(*self.scope.get_uncertainty_names(), style=style)

	def lever_selectors(self, style='hist'):
		return self.selectors(*self.scope.get_lever_names(), style=style)

	def lever_viewers(self, style='kde'):
		return self.viewers(*self.scope.get_lever_names(), style=style)

	def measure_selectors(self, style='hist'):
		return self.selectors(*self.scope.get_measure_names(), style=style)

	def measure_viewers(self, style='kde'):
		return self.viewers(*self.scope.get_measure_names(), style=style)

	def complete(self, measure_style='kde'):
		return widget.VBox([
			self.status(),
			widget.HTML("<h3>Policy Levers</h3>"),
			self.selectors(*self.scope.get_lever_names()),
			widget.HTML("<h3>Exogenous Uncertainties</h3>"),
			self.selectors(*self.scope.get_uncertainty_names()),
			widget.HTML("<h3>Performance Measures</h3>"),
			self._measure_notes(),
			self.measure_viewers(style=measure_style),
		])

	def _measure_notes(self, style='kde'):
		basecolor = colors.DEFAULT_BASE_COLOR
		highlightcolor = colors.DEFAULT_HIGHLIGHT_COLOR
		basecolor_name = colors.get_colour_name(basecolor, case=str.lower)
		highlight_name = colors.get_colour_name(highlightcolor, case=str.lower)
		if style == 'kde':
			txt = f"""<div style="line-height:125%;margin:9px 0px">
			The <span style="font-weight:bold;color:{basecolor}">{basecolor_name}</span> curve
			depicts the unconditional distribution of performance measures in the data across
			all cases, while the <span style="font-weight:bold;color:{highlightcolor}">{highlight_name}</span> 
			curve depicts the distribution of performance measures conditional on the constraints.
			</div>"""
		else:
			txt = f"""<div style="line-height:125%;margin:9px 0px">
			The <span style="font-weight:bold;color:{basecolor}">{basecolor_name}</span> bars
			depict the unconditional frequency of performance measures in the data across
			all cases, while the <span style="font-weight:bold;color:{highlightcolor}">{highlight_name}</span> 
			curve depicts the frequency of performance measures conditional on the constraints.
			</div>"""
		return widget.HTML(txt)

	def two_way(self, key=None, reset=False):
		if key in self._two_way and not reset:
			return self._two_way[key]

		from ..viz.dataframe_viz import DataFrameViewer
		self._two_way[key] = DataFrameViewer(self.data, box=self.box, scope=self.scope)
		return self._two_way[key]