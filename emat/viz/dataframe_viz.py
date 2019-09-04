

import numpy
import plotly.graph_objs as go
from ipywidgets import HBox, VBox, Dropdown, Label, Text
from . import colors
from ..util.naming import clean_name

class DataFrameViewer(HBox):

	def __init__(
			self,
			df,
			selection=None,
			box=None,
			scope=None,
			target_marker_opacity=500,
			minimum_marker_opacity=0.25,
	):
		self.df = df

		self.selection = selection
		self.box = box
		self.scope = scope

		self.x_axis_choose = Dropdown(
			options=self.df.columns,
			#description='X Axis',
			value=self.df.columns[0],
		)

		self.x_axis_scale = Dropdown(
			options=['linear',],
			value='linear',
		)

		self.y_axis_choose = Dropdown(
			options=self.df.columns,
			#description='Y Axis',
			value=self.df.columns[-1],
		)

		self.y_axis_scale = Dropdown(
			options=['linear',],
			value='linear',
		)


		self.selection_choose = Dropdown(
			options=['None', 'Box', 'Expr'],
			value='None',
		)

		self.selection_expr = Text(
			value='True',
			disabled=True,
		)

		self.axis_choose = VBox(
			[
				Label("X Axis"),
				self.x_axis_choose,
				self.x_axis_scale,
				Label("Y Axis"),
				self.y_axis_choose,
				self.y_axis_scale,
				Label("Selection"),
				self.selection_choose,
				self.selection_expr,
			],
			layout=dict(
				overflow='hidden',
			)
		)

		self.minimum_marker_opacity = minimum_marker_opacity
		self.target_marker_opacity = target_marker_opacity
		marker_opacity = self._compute_marker_opacity()

		self._x_data_range = [0,1]
		self._y_data_range = [0,1]

		self.scattergraph = go.Scattergl(
			x=None,
			y=None,
			mode = 'markers',
			marker=dict(
				opacity=marker_opacity[0],
				color=colors.DEFAULT_BASE_COLOR,
			),
		)

		self.x_hist = go.Histogram(
			x=None,
			name='x density',
			marker=dict(
				color=colors.DEFAULT_BASE_COLOR,
				#opacity=0.7,
			),
			yaxis='y2',
			bingroup='xxx',
		)

		self.y_hist = go.Histogram(
			y=None,
			name='y density',
			marker=dict(
				color=colors.DEFAULT_BASE_COLOR,
				#opacity=0.7,
			),
			xaxis='x2',
			bingroup='yyy',
		)

		self.scattergraph_s = go.Scattergl(
			x=None,
			y=None,
			mode = 'markers',
			marker=dict(
				opacity=marker_opacity[1],
				color=colors.DEFAULT_HIGHLIGHT_COLOR,
			),
		)

		self.x_hist_s = go.Histogram(
			x=None,
			marker=dict(
				color=colors.DEFAULT_HIGHLIGHT_COLOR,
				#opacity=0.7,
			),
			yaxis='y2',
			bingroup='xxx',
		)

		self.y_hist_s = go.Histogram(
			y=None,
			marker=dict(
				color=colors.DEFAULT_HIGHLIGHT_COLOR,
				#opacity=0.7,
			),
			xaxis='x2',
			bingroup='yyy',
		)

		self.graph = go.FigureWidget([
			self.scattergraph,
			self.x_hist,
			self.y_hist,
			self.scattergraph_s,
			self.x_hist_s,
			self.y_hist_s,
		])


		self.graph.layout=dict(
			xaxis=dict(
				domain=[0, 0.85],
				showgrid=True,
				#title=self.df.columns[0],
			),
			yaxis=dict(
				domain=[0, 0.85],
				showgrid=True,
				#title=self.df.columns[-1],
			),

			xaxis2=dict(
				domain=[0.85, 1],
				showgrid=True,
				zeroline=True,
				zerolinecolor='#FFF',
				zerolinewidth=4,
			),
			yaxis2=dict(
				domain=[0.85, 1],
				showgrid=True,
				zeroline=True,
				zerolinecolor='#FFF',
				zerolinewidth=4,
			),

			barmode="overlay",
			showlegend=False,
			margin=dict(l=10, r=10, t=10, b=10),
		)

		self.x_axis_choose.observe(self._observe_change_column_x, names='value')
		self.y_axis_choose.observe(self._observe_change_column_y, names='value')
		self.selection_choose.observe(self._on_change_selection_choose, names='value')
		self.selection_expr.observe(self._on_change_selection_expr, names='value')

		self.set_x(self.df.columns[0])
		self.set_y(self.df.columns[-1])
		self.draw_box()

		super().__init__(
			[
				self.graph,
				self.axis_choose,
			],
			layout=dict(
				align_items='center',
			)
		)

	def _get_shortname(self, name):
		if self.scope is None:
			return name
		return self.scope.shortname(name)

	def _compute_marker_opacity(self):
		if self.selection is None:
			marker_opacity = 1.0
			if len(self.df) > self.target_marker_opacity:
				marker_opacity = self.target_marker_opacity / len(self.df)
			if marker_opacity < self.minimum_marker_opacity:
				marker_opacity = self.minimum_marker_opacity
			return marker_opacity, 1.0
		else:
			marker_opacity = [1.0, 1.0]
			n_selected = int(self.selection.sum())
			n_unselect = len(self.df) - n_selected
			if n_unselect > self.target_marker_opacity:
				marker_opacity[0] = self.target_marker_opacity / n_unselect
			if marker_opacity[0] < self.minimum_marker_opacity:
				marker_opacity[0] = self.minimum_marker_opacity

			if n_selected > self.target_marker_opacity:
				marker_opacity[1] = self.target_marker_opacity / n_selected
			if marker_opacity[1] < self.minimum_marker_opacity:
				marker_opacity[1] = self.minimum_marker_opacity
			return marker_opacity

	@property
	def _x_data_width(self):
		w = self._x_data_range[1] - self._x_data_range[0]
		if w > 0:
			return w
		return 1

	@property
	def _y_data_width(self):
		w = self._y_data_range[1] - self._y_data_range[0]
		if w > 0:
			return w
		return 1

	def _observe_change_column_x(self, payload):
		self.set_x(payload['new'])

	def set_x(self, col):
		"""
		Set the new X axis data.

		Args:
			col (str or array-like):
				The name of the new `x` column in `df`, or a
				computed array or pandas.Series of values.
		"""
		with self.graph.batch_update():
			if isinstance(col, str):
				self._x = x = self.df[col]
				self.graph.layout.xaxis.title = self._get_shortname(col)
			else:
				self._x = x = col
				try:
					self.graph.layout.xaxis.title = self._get_shortname(col.name)
				except:
					pass
			if self.selection is None:
				self.graph.data[0].x = x
				self.graph.data[3].x = None
				self.graph.data[1].x = x
				self.graph.data[4].x = None
			else:
				self.graph.data[0].x = x[~self.selection]
				self.graph.data[3].x = x[self.selection]
				self.graph.data[1].x = x
				self.graph.data[4].x = x[self.selection]
			self._x_data_range = [x.min(), x.max()]
			self.graph.layout.xaxis.range = (
				self._x_data_range[0] - self._x_data_width * 0.07,
				self._x_data_range[1] + self._x_data_width * 0.07,
			)
			self.draw_box()

	def _observe_change_column_y(self, payload):
		self.set_y(payload['new'])

	def set_y(self, col):
		"""
		Set the new Y axis data.

		Args:
			col (str or array-like):
				The name of the new `y` column in `df`, or a
				computed array or pandas.Series of values.
		"""
		with self.graph.batch_update():
			if isinstance(col, str):
				self._y = y = self.df[col]
				self.graph.layout.yaxis.title = self._get_shortname(col)
			else:
				self._y = y = col
				try:
					self.graph.layout.yaxis.title = self._get_shortname(col.name)
				except:
					pass
			if self.selection is None:
				self.graph.data[0].y = y
				self.graph.data[3].y = None
				self.graph.data[2].y = y
				self.graph.data[5].y = None
			else:
				self.graph.data[0].y = y[~self.selection]
				self.graph.data[3].y = y[self.selection]
				self.graph.data[2].y = y
				self.graph.data[5].y = y[self.selection]
			self._y_data_range = [y.min(), y.max()]
			self.graph.layout.yaxis.range = (
				self._y_data_range[0] - self._y_data_width * 0.07,
				self._y_data_range[1] + self._y_data_width * 0.07,
			)
			self.draw_box()

	def change_selection(self, new_selection):
		if new_selection is None:
			self.selection = None
			# Update Selected Portion of Scatters
			x = self._x
			y = self._y
			self.graph.data[0].x = x
			self.graph.data[0].y = y
			self.graph.data[3].x = None
			self.graph.data[3].y = None
			marker_opacity = self._compute_marker_opacity()
			self.graph.data[0].marker.opacity = marker_opacity[0]
			self.graph.data[3].marker.opacity = marker_opacity[1]
			# Update Selected Portion of Histograms
			self.graph.data[4].x = None
			self.graph.data[5].y = None
			self.draw_box()
			return

		if new_selection.size != len(self.df):
			raise ValueError(f"new selection size ({new_selection.size}) "
							 f"does not match length of data ({len(self.df)})")
		self.selection = new_selection
		with self.graph.batch_update():
			# Update Selected Portion of Scatters
			x = self._x
			y = self._y
			# x = self.df[self.x_axis_choose.value]
			# y = self.df[self.y_axis_choose.value]
			self.graph.data[0].x = x[~self.selection]
			self.graph.data[0].y = y[~self.selection]
			self.graph.data[3].x = x[self.selection]
			self.graph.data[3].y = y[self.selection]
			marker_opacity = self._compute_marker_opacity()
			self.graph.data[0].marker.opacity = marker_opacity[0]
			self.graph.data[3].marker.opacity = marker_opacity[1]
			# Update Selected Portion of Histograms
			self.graph.data[4].x = x[self.selection]
			self.graph.data[5].y = y[self.selection]
			self.draw_box()

	def draw_box(self, box=None):
		from ..scope.box import Bounds
		x_label = self.x_axis_choose.value
		y_label = self.y_axis_choose.value

		if box is None:
			box = self.box
		if box is None:
			self.graph.layout.shapes = []
		else:
			if x_label in box.thresholds or y_label in box.thresholds:
				x_lo, x_hi = None, None
				y_lo, y_hi = None, None
				if isinstance(box.thresholds.get(x_label), Bounds):
					x_lo, x_hi = box.thresholds[x_label]
				if isinstance(box.thresholds.get(y_label), Bounds):
					y_lo, y_hi = box.thresholds[y_label]
				if x_lo is None:
					x_lo = self.df[x_label].min()-self._x_data_width
				if x_hi is None:
					x_hi = self.df[x_label].max()+self._x_data_width
				if y_lo is None:
					y_lo = self.df[y_label].min()-self._y_data_width
				if y_hi is None:
					y_hi = self.df[y_label].max()+self._y_data_width

				self.graph.layout.shapes=[
					# Rectangle reference to the axes
					go.layout.Shape(
						type="rect",
						xref="x1",
						yref="y1",
						x0=x_lo,
						y0=y_lo,
						x1=x_hi,
						y1=y_hi,
						line=dict(
							width=0,
						),
						fillcolor=colors.DEFAULT_BOX_BG_COLOR,
						opacity=0.2,
						layer="below",
					),
				]
			else:
				self.graph.layout.shapes=[]

	def _selection_eval(self, txt):
		df = self.df.rename(columns={i: clean_name(i) for i in self.df.columns})
		return df.eval(txt).astype(bool)

	def _on_change_selection_choose(self, payload):
		if payload['new'] == 'Expr':
			self.selection_expr.disabled = False
		else:
			self.selection_expr.disabled = True
		if payload['new'] == 'Box':
			self.change_selection(self.box.inside(self.df))
		if payload['new'] == 'None':
			self.change_selection(None)

	def _on_change_selection_expr(self, payload):
		expression = payload['new']
		try:
			sel = self._selection_eval(expression)
		except Exception as err:
			#print("FAILED ON EVAL\n",expression, err)
			pass
		else:
			try:
				self.change_selection(sel)
			except Exception as err:
				#print("FAILED ON SETTING\n", expression, err)
				pass
			else:
				#print("PASSED", expression)
				pass

	def _on_box_change(self, selection=None):
		if self.selection_choose.value == 'Box':
			if selection is None:
				selection = self.box.inside(self.df)
			self.change_selection(selection)
		else:
			with self.graph.batch_update():
				self.draw_box()