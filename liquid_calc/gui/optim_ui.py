# -*- coding: utf-8 -*-
__author__ = "Benedict J Heinen"
__copyright__ = "Copyright 2018, Benedict J Heinen"
__email__ = "benedict.heinen@gmail.com"

from PyQt5.QtCore import Qt, pyqtSignal                                   
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import QWidget, QFrame, QGridLayout, QVBoxLayout, \
                            QHBoxLayout, QGroupBox, QPushButton, QLineEdit, \
                            QComboBox, QTableWidget, QTableWidgetItem, \
                            QLabel, QCheckBox, QButtonGroup, QRadioButton, \
                            QScrollArea, QSplitter
import numpy as np
from scipy.optimize import minimize
import os
import datetime

from . import plot_widgets
from . import utility
from core import data_manip
import core.core as core



class OptimUI(QWidget):
    
    # Create custom signal to link Optim/Results UI
    results_changed = pyqtSignal()

    # Options to pass to scipy.optimise.minimize solver
    # Set disp to 1 for verbose output of solver progress
    # See SciPy docs for further info
    minimisation_options = {'disp': 0,
                            'maxiter': 15000,
                            'maxfun': 15000,
                            'ftol': 2.22e-8,
                            'gtol': 1e-10
                            }
    # Use limited-memory BFGS code for optimising rho
    # See http://users.iems.northwestern.edu/~nocedal/lbfgsb.html for details
    op_method = 'L-BFGS-B'
    
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        
        # Make Config Widget
        self.optim_config_widget = OptimConfigWidget()
        
        # Make vertical line separator
        self.vline = QFrame()
        self.vline.setFrameShape(QFrame.VLine)
        self.vline.setFrameShadow(QFrame.Sunken)
        self.vline.setObjectName("vline")
        
        self.optim_plot_widget = plot_widgets.OptimPlotWidget()
        self.plot_scroll_area = QScrollArea()
        self.plot_scroll_area.setWidget(self.optim_plot_widget)
        self.plot_scroll_area.setWidgetResizable(True)
        self.plot_scroll_area.setFrameShape(QFrame.NoFrame)

        self.config_scroll_area = QScrollArea()
        self.config_scroll_area.setFrameShape(QFrame.NoFrame)
        self.config_scroll_area.setWidget(self.optim_config_widget)
        self.config_scroll_area.setWidgetResizable(True)
        #self.scroll_area.setFixedHeight(1080)
        
        
        self.hsplitter = QSplitter(Qt.Horizontal)
        
        self.hsplitter.addWidget(self.config_scroll_area)
        self.hsplitter.addWidget(self.plot_scroll_area)
        
        self.layout.addWidget(self.hsplitter)
        #self.layout.addWidget(self.config_scroll_area)        
        #self.layout.addWidget(self.vline)
        #self.layout.addWidget(self.plot_scroll_area)

        self.layout.setStretch(0,1)
        self.layout.setStretch(1,0)
        self.layout.setStretch(2,5)


        self.setLayout(self.layout)


        self.data = {'cor_x': np.asarray([]), 'cor_y': np.asarray([]),
                     'cor_x_cut': np.asarray([]), 'cor_y_cut': np.asarray([]),
                     'sq_x':  np.asarray([]), 'sq_y':  np.asarray([]),
                     'fr_x':  np.asarray([]), 'fr_y':  np.asarray([]),
                     'int_func': np.asarray([]), 'impr_int_func': np.asarray([]),
                     'impr_fr_x': np.asarray([]), 'impr_fr_y': np.asarray([]),
                     'impr_iq_x': np.asarray([]), 'mod_func': 'None'}
        
        self.create_signals()

    def create_signals(self):        
        self.optim_config_widget.data_options_gb.qmax_check.stateChanged.connect(self.plot_data)
        self.optim_config_widget.data_options_gb.qmax_input.textChanged.connect(self.plot_data)
        self.optim_config_widget.data_options_gb.qmin_check.stateChanged.connect(self.plot_data)
        self.optim_config_widget.data_options_gb.qmin_input.textChanged.connect(self.plot_data)
        self.optim_config_widget.data_options_gb.calc_sq_btn.clicked.connect(self.on_click_calc_sq)
        self.optim_config_widget.data_options_gb.smooth_data_check.toggled.connect(self.smooth_check_toggled)
        self.optim_config_widget.data_options_gb.window_length_input.textChanged.connect(self.smooth_check_toggled)
        self.optim_config_widget.data_options_gb.poly_order_input.textChanged.connect(self.smooth_check_toggled)
        self.optim_config_widget.optim_options_gb.opt_button.clicked.connect(self.on_click_refine)
      

    def plot_data(self):
        # Plots the data, no through update when this is changed
        # so the other data (S(Q) & F(r)) are cleared first
        _ea = np.asarray([])
        self.data['iq_x'] = _ea
        self.data['impr_iq_x'] = _ea
        self.data['sq_y'] = _ea
        self.data['fr_x'] = _ea 
        self.data['fr_y'] = _ea
        self.data['int_func'] = _ea
        self.data['impr_int_func'] = _ea
        self.data['impr_fr_x'] = _ea
        self.data['impr_fr_y'] = _ea
        self.data['cor_x_cut'] = _ea
        self.data['cor_y_cut'] = _ea
        
        qmax_cut = (
                self.optim_config_widget.data_options_gb.qmax_check.isChecked() 
                and self.optim_config_widget.data_options_gb.qmax_input.text()
                )
        
        qmin_cut = (
                self.optim_config_widget.data_options_gb.qmin_check.isChecked()
                and self.optim_config_widget.data_options_gb.qmin_input.text())
        
        # Cut q at qman first (if selected) and define cor_x_cut
        if qmax_cut:
            # Get q_max to cut at 
            _qmax = np.float(self.optim_config_widget.data_options_gb.qmax_input.text())
            # cut q data at qmax
            _cut = np.where(self.data['cor_x'] < _qmax)
            self.data['cor_x_cut'] = self.data['cor_x'][_cut]
            self.data['cor_y_cut'] = self.data['cor_y'][_cut]
        
        # Define cor_x_cut = cor_x for simpler plotting logic
        else:
            self.data['cor_x_cut'] = self.data['cor_x']
            self.data['cor_y_cut'] = self.data['cor_y']
        
        # Cut at qmin if selected
        if qmin_cut:
            _qmin = np.float(self.optim_config_widget.data_options_gb.qmin_input.text())
            # Take first intensity value after q_min 
            # Catch empty array error caused by no data:
            try:
                _fill_val = self.data['cor_y'][np.argmax(self.data['cor_x_cut'] > _qmin)]
                _cut = self.data['cor_y'][np.where(self.data['cor_x_cut'] > _qmin)]
                _padding = np.asarray([_fill_val]*(len(self.data['cor_x_cut']) - len(_cut)))
                self.data['cor_y_cut'] = np.concatenate((_padding, _cut))
            #print('corycut', self.data['cor_y_cut'])
            except ValueError:
                pass
            #self.data['cor_y_cut'] = self.data['cor_y_cut'][_cut]
        self.data['modification'] = 1
        if self.optim_config_widget.data_options_gb.smooth_data_check.isChecked():
            self.smooth_check_toggled()
        else:
            self.optim_plot_widget.update_plots(self.data)
    

    def on_click_calc_sq(self):
        # Run only if data present
        if not self.data['cor_x_cut'].size:
            return
        # Run only if composition set
        _composition = self.optim_config_widget.composition_gb.get_composition_dict()
        if not _composition:
            return
        # Delete previous refined data
        self.data['impr_iq_x'] = np.asarray([])
        self.data['impr_fr_x'] = np.asarray([])
        self.data['impr_fr_y'] = np.asarray([])
        self.data['impr_int_func'] = np.asarray([])
        # Get modification function to use
        self.data['mod_func'] = self.optim_config_widget.data_options_gb.mod_func_input.currentText()
        if self.data['mod_func'] == 'Cosine-window':
            try:
                self.data['window_start'] = np.float(self.optim_config_widget.data_options_gb.window_start_input.text())
            except ValueError:
                print('Please set limit for Cosine-window function')
                return
        else:
            self.data['window_start']=None
        # Get S(Q) method
        if self.optim_config_widget.data_options_gb.al_btn.isChecked():
            _method = 'ashcroft-langreth'
        elif self.optim_config_widget.data_options_gb.fb_btn.isChecked():
            _method='faber-ziman'
        # Get rho 0
        _rho_0 = np.float(self.optim_config_widget.composition_gb.density_input.text())
        self.data['iq_x'] = self.data['cor_x_cut']
        self.data['sq_y'] = core.calc_structure_factor(self.data['cor_x_cut'], 
                                                       self.data['cor_y_cut'], 
                                                       _composition, _rho_0,
                                                       method=_method)
        _S_inf = core.calc_S_inf(_composition, self.data['cor_x_cut'])
        self.data['int_func'] = self.data['sq_y'] - _S_inf
        self.data['fr_x'], self.data['fr_y'] = core.calc_F_r(self.data['iq_x'], self.data['int_func'], _rho_0,
                                                             mod_func=self.data['mod_func'], window_start=self.data['window_start'])
        self.data['modification'] = core.get_mod_func(self.data['iq_x'], self.data['mod_func'], self.data['window_start'])
        self.optim_plot_widget.update_plots(self.data)


    def on_click_refine(self):
        # Delete previous chi_sq & refined density
        try:
            del self.data['chi_sq']
            del self.data['refined_rho']
        except KeyError:
            pass
        # Don't run if sq/int_func not calculated yet
        if not self.data['int_func'].size:
            return
        # Get modification function to use again
        self.data['mod_func'] = self.optim_config_widget.data_options_gb.mod_func_input.currentText()
        if self.data['mod_func'] == 'Cosine-window':
            try:
                self.data['window_start'] = np.float(self.optim_config_widget.data_options_gb.window_start_input.text())
            except ValueError:
                print('Please set limit for Cosine-window function')
                return
        _composition = self.optim_config_widget.composition_gb.get_composition_dict()
        # Don't run if no composition set
        if not _composition:
            return
        # Get S(Q) method
        if self.optim_config_widget.data_options_gb.al_btn.isChecked():
            _method = 'ashcroft-langreth'
        elif self.optim_config_widget.data_options_gb.fb_btn.isChecked():
            _method='faber-ziman'
        # Get density
        _rho_0 = np.float(self.optim_config_widget.composition_gb.density_input.text())
        # Get r_min, d_pq
        _r_min = np.float(self.optim_config_widget.optim_options_gb.rmin_input.text())
        #_d_pq = np.float(self.optim_config_widget.optim_options_gb.d_pq_input.text())
        # Functionality for d_pq removed for now
        _d_pq = 2.9
        # Get no. iterations for Eggert refinement
        _n_iter = np.int(self.optim_config_widget.optim_options_gb.niter_input.text())
        if self.optim_config_widget.optim_options_gb.opt_check.isChecked():
            # Get bounds but don't continue if none set
            try:
                _lb = np.float(self.optim_config_widget.optim_options_gb.lb_input.text())
                _ub = np.float(self.optim_config_widget.optim_options_gb.ub_input.text())
            except ValueError:
                return
            _bounds = ((_lb, _ub),)
            _args = (self.data['cor_x_cut'], self.data['cor_y_cut'],
                     _composition, _r_min, _d_pq, _n_iter, _method, 
                     self.data['mod_func'], self.data['window_start'], 1)
            print('\n*************************\n')
            print('Finding optimal density...')
            _opt_result = minimize(core.calc_impr_interference_func,
                                   _rho_0, bounds=_bounds, args=_args,
                                   options=self.minimisation_options,
                                   method=self.op_method)
            self.data['refined_rho'] = _opt_result.x[0]
            _rho_temp = self.data['refined_rho']
            print('Refined density = ', _rho_temp)
            print('Chi^2 = ', _opt_result.fun, '\n')
            self.optim_config_widget.optim_results_gb.density_output.setText('{:.4e}'.format(self.data['refined_rho']))
            _mass_density = core.conv_density(_rho_temp, _composition)
            self.optim_config_widget.optim_results_gb.mass_density.setText('{0:.3f}'.format(_mass_density))
        else:
            _rho_temp = _rho_0
                
        _args = (self.data['cor_x_cut'], self.data['int_func'],
                 _composition, _r_min, _d_pq, _n_iter, _method, 
                 self.data['mod_func'], self.data['window_start'], 0)
        self.data['impr_int_func'], self.data['chi_sq'] = core.calc_impr_interference_func(_rho_temp, *_args)
        self.optim_config_widget.optim_results_gb.chi_sq_output.setText('{:.4e}'.format(self.data['chi_sq']))
        # Calculated improved F_r
        self.data['impr_fr_x'], self.data['impr_fr_y'] = core.calc_F_r(self.data['iq_x'], self.data['impr_int_func'], _rho_temp,
                                                                       mod_func = self.data['mod_func'], window_start=self.data['window_start'])
        self.data['impr_iq_x'] = self.data['iq_x']
        # Set modification function to None so it is not plotted this time
        _mod_func = self.data['mod_func']
        self.data['mod_func'] = 'None'
        #Plot data
        self.optim_plot_widget.update_plots(self.data)
        self.data['mod_func'] = _mod_func
        
        # Save refinement parameters to file
        if self.optim_config_widget.data_options_gb.smooth_data_check.isChecked():
            _smooth_bool = 'Y'
        else:
            _smooth_bool = 'N'
        
        if self.optim_config_widget.optim_options_gb.opt_check.isChecked():
            _refine_density_bool = 'Y'
            _refine_density_log = (
                                   'Solver : ' + self.op_method + '\n' +
                                   'Lower bound : ' + str(_lb) + '\n' +
                                   'Upper bound : ' + str(_ub) + '\n' +
                                   '*'*25 + '\n' +
                                   str(_opt_result) + '\n' +
                                   '*'*25 + '\n\n' +
                                   'Refined density : ' + str(self.data['refined_rho']) + ' (at/A^3)\n' +
                                   '                  ' + str(_mass_density) + ' (g/cm3)\n' +
                                   'Chi^2 : ' + str(self.data['chi_sq']) + '\n'
                                   )
        else:
            _refine_density_bool = 'N'
            _refine_density_log = ('Chi^2 : ' + str(self.data['chi_sq']) + '\n')
        
        log_string = (
                      'refinement_log\n' +
                      core.__name__ + ' v' + core.__version__ + '\n\n' +
                      '-'*25 + '\n' +
                      'Data File : ' + self.base_filename + '\n' +
                      'Composition [Element: (Z, Charge, n)]: ' + str(_composition) + '\n' +
                      'Q_min : ' + self.optim_config_widget.data_options_gb.qmin_input.text() + '\n' +
                      'Q_max : ' + self.optim_config_widget.data_options_gb.qmax_input.text() + '\n' +
                      'Data smoothing? : ' + _smooth_bool + '\n' +
                      'Modification function : ' + self.data['mod_func'] + '\n' +
                      'Cosine window start : ' + str(self.data['window_start']) + '\n' +
                      'S(Q) formulation : ' + _method + '\n' +
                      'Density : ' + str(_rho_0) + '\n' +
                      'r_min : ' + str(_r_min) + '\n' + 
                      'Number iterations (Eggert) : ' + str(_n_iter) + '\n' +
                      '*'*25 + '\n' +
                      'Density refined? : ' + _refine_density_bool + '\n' +
                      _refine_density_log
                      )
        # Append log mode
        append_log_mode = 1
        # Append to log file or overwrite?
        if append_log_mode:
            _log_file = open(os.path.join(os.path.dirname(self.base_filename), 'refinement.log'),'ab')
            # Add timestamp to top of log_string
            log_string = ('#'*30 + '\n' + 
                          str(datetime.datetime.now()) + '\n' + 
                          '#'*30 + '\n' +
                          log_string
                          )
            np.savetxt(_log_file, [log_string], fmt='%s')
            _log_file.close()
        else:
            _log_file = self.base_filename + '_refinement.log'
            np.savetxt(_log_file, [log_string], fmt='%s')
        
        self.results_changed.emit()

    def smooth_check_toggled(self):
        if self.optim_config_widget.data_options_gb.smooth_data_check.isChecked():
            self.optim_config_widget.data_options_gb.window_length_lbl.setEnabled(True)
            self.optim_config_widget.data_options_gb.window_length_input.setEnabled(True)
            self.optim_config_widget.data_options_gb.poly_order_lbl.setEnabled(True)
            self.optim_config_widget.data_options_gb.poly_order_input.setEnabled(True)
            if not self.data['cor_y_cut'].size:
                return
            try:
                _window_length = np.int(self.optim_config_widget.data_options_gb.window_length_input.text()) 
                _poly_order = np.int(self.optim_config_widget.data_options_gb.poly_order_input.text())
            except ValueError:
                return

            if _poly_order >= _window_length:
                print('Warning: polyorder must be less than window_length')
                return
            
            self.data['cor_y_cut'] = data_manip.smooth_data(self.data['cor_y_cut'],
                                                            window_length = _window_length,
                                                            poly_order = _poly_order)
        else:
            self.optim_config_widget.data_options_gb.window_length_lbl.setEnabled(False)
            self.optim_config_widget.data_options_gb.window_length_input.setEnabled(False)
            self.optim_config_widget.data_options_gb.poly_order_lbl.setEnabled(False)
            self.optim_config_widget.data_options_gb.poly_order_input.setEnabled(False)
            # If removing the smoothing - replot and calculate data
            self.plot_data()
        # Update the plots
        self.optim_plot_widget.update_plots(self.data)


class OptimConfigWidget(QWidget):

    def __init__(self):
        super(OptimConfigWidget, self).__init__()

        self.vlayout = QVBoxLayout()
        self.vlayout.setContentsMargins(0, 0, 5, 0)
        self.vlayout.setSpacing(10)

        self.composition_gb = CompositionGroupBox()
        self.data_options_gb = DataOptionsGroupBox()
        self.optim_options_gb = OptimOptionsGroupBox()
        self.optim_results_gb = OptimResultsGroupBox()

        self.vlayout.addWidget(self.composition_gb)           
        self.vlayout.addWidget(self.data_options_gb)
        self.vlayout.addWidget(self.optim_options_gb)
        self.vlayout.addWidget(self.optim_results_gb)      
        self.setLayout(self.vlayout)
        
        self.create_signals()

    def create_signals(self):
        self.optim_options_gb.toggled.connect(self._toggle_results_gb)
        self.optim_options_gb.opt_check.stateChanged.connect(self._toggle_density_refine)
           
    def _toggle_results_gb(self, on):
        self.optim_results_gb.setEnabled(on)
    
    def _toggle_density_refine(self, state):
        self.optim_results_gb.density_output.setEnabled(state)
        self.optim_results_gb.density_output_label.setEnabled(state)
        self.optim_results_gb.mass_density.setEnabled(state)
        self.optim_results_gb.mass_density_label.setEnabled(state)
    
class CompositionGroupBox(QGroupBox):
    
    
    __data_path = os.path.join(os.path.abspath(os.getcwd()), 'data')
    _element_dict = np.load(os.path.join(__data_path,'pt_data.npy')).item()
    
    def __init__(self, *args):
        super(CompositionGroupBox, self).__init__(*args)
        self.setTitle('Composition')
        self.setAlignment(Qt.AlignLeft)
        self.setStyleSheet('GroupBox::title{subcontrol-origin: margin; subcontrol-position: top left;}')
        
        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()
        
    def create_widgets(self):
        
        self.add_element_btn = QPushButton("Add")
        self.delete_element_btn = QPushButton("Delete")
        
        self.density_lbl = QLabel("Density:")
        self.density_input = QLineEdit("1.0")
        
        self.mass_density_label = QLabel('g/cm<sup>3</sup>')
        self.mass_density = QLineEdit('')
        
        self.composition_table = QTableWidget()
        
        
    def style_widgets(self):  
        
        self.density_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        self.density_input.setAlignment(Qt.AlignRight)
        self.density_input.setValidator(QDoubleValidator())
        self.density_input.setMaximumWidth(100)
        
        self.mass_density.setAlignment(Qt.AlignRight)
        self.mass_density.setMaximumWidth(100)
        
        self.mass_density.setReadOnly(True)
        self.mass_density.isReadOnly()

        self.composition_table.setColumnCount(4)
        self.composition_table.horizontalHeader().setVisible(True)
        self.composition_table.verticalHeader().setVisible(False)
        self.composition_table.setContentsMargins(0 , 0, 0, 0)
        self.composition_table.horizontalHeader().setStretchLastSection(True)
        #self.composition_table.setFrameStyle(False)
        self.composition_table.setHorizontalHeaderLabels(['Element', 'Z', 'Charge', 'n'])
        self.composition_table.horizontalHeaderItem(0).setToolTip('Atomic element ')
        self.composition_table.horizontalHeaderItem(1).setToolTip('Atomic number ')
        self.composition_table.horizontalHeaderItem(2).setToolTip('Charge ')
        self.composition_table.horizontalHeaderItem(3).setToolTip('Proportion of compound ')
 
        # Set the alignment to the headers
        self.composition_table.horizontalHeaderItem(0).setTextAlignment(Qt.AlignLeft)
        self.composition_table.horizontalHeaderItem(1).setTextAlignment(Qt.AlignHCenter)
        self.composition_table.horizontalHeaderItem(2).setTextAlignment(Qt.AlignHCenter)
        self.composition_table.horizontalHeaderItem(3).setTextAlignment(Qt.AlignHCenter)

        self.composition_table.setColumnWidth(0, 71)
        self.composition_table.setColumnWidth(1, 66)
        self.composition_table.setColumnWidth(2, 66)
        self.composition_table.setColumnWidth(3, 66)
        #self.composition_table.setSelectionBehaviour(QAbstractItemView.SelectRows)
        
        #self.composition_table.element_editor.setContentsMargins(0, 0, 0, 0)                                              
        self.composition_table.setItemDelegate(utility.ValidatedItemDelegate(self))

        
        
    def create_layout(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 7)
        self.main_layout.setSpacing(5)

        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(15)
        self.button_layout.addWidget(self.add_element_btn)
        self.button_layout.addWidget(self.delete_element_btn)

        self.density_layout = QGridLayout()
        self.density_layout.addWidget(self.density_lbl, 0, 0)
        self.density_layout.addWidget(self.density_input, 0, 1)
        self.density_layout.addWidget(QLabel('atoms/A<sup>3</sup>'), 0, 2)
        self.density_layout.addWidget(self.mass_density, 1, 1)
        self.density_layout.addWidget(self.mass_density_label, 1, 2)
        
        self.main_layout.addLayout(self.button_layout)
        self.main_layout.addWidget(self.composition_table)
        self.main_layout.addLayout(self.density_layout)

        self.setLayout(self.main_layout)      
     
  
    
    def create_signals(self):
        self.delete_element_btn.clicked.connect(self.delete_row)
        self.add_element_btn.clicked.connect(self.add_row)
        self.density_input.textChanged.connect(self.update_mass_density)

     
    def add_row(self):
        _row_position = self.composition_table.rowCount()
        self.composition_table.insertRow(_row_position)
   
        _element_editor = QComboBox()
        _element_editor.setStyleSheet('QComboBox {border: 0px ;} ')
        for index, element in enumerate(CompositionGroupBox._element_dict):
            _element_editor.insertItem(index, element)
        #_element_editor.setStyle(QStyleFactory.create('Cleanlooks'))
        self.composition_table.setCellWidget(_row_position, 0, _element_editor)
        _element_editor.setCurrentIndex(30)
        #self.composition_table.setItem(_row_position , 0, QTableWidgetItem('Ga'))
        self.composition_table.setItem(_row_position , 1, QTableWidgetItem('31'))
        self.composition_table.setItem(_row_position , 2, QTableWidgetItem('0'))
        self.composition_table.setItem(_row_position , 3, QTableWidgetItem('1'))
        
        self.composition_table.item(_row_position, 1).setFlags( Qt.ItemIsSelectable |  Qt.ItemIsEnabled )
        self.composition_table.item(_row_position, 1).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.composition_table.item(_row_position, 1).setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.composition_table.item(_row_position, 2).setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.composition_table.item(_row_position, 3).setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        
        # Create Signal
        _element_editor.currentIndexChanged.connect(self.update_cb_val)
        
        self.update_mass_density()

    def delete_row(self):
        # Selects last row if none selected by user
        _selected_row = self.composition_table.currentRow()
        if _selected_row == -1:
            _selected_row = self.composition_table.rowCount() - 1
        else:
            pass
        self.composition_table.removeRow(_selected_row)
        self.update_mass_density()
        
      
    def update_cb_val(self):
        _cb_widget = self.sender()
        _current_row = self.composition_table.indexAt(_cb_widget.pos()).row()        
        _new_element = str(_cb_widget.currentText())
        _new_Z_val = str(CompositionGroupBox._element_dict[_new_element])
        self.composition_table.item(_current_row, 1).setText(_new_Z_val)
        self.update_mass_density()
      
    def get_composition_dict(self):
        '''Return composition dictionary'''
        # Form of dictionary is col 0 is key, val is tuple(col1,col2,col3)
        _composition_dict = {}
        _key_list = list(CompositionGroupBox._element_dict.keys())
        _val_list = list(CompositionGroupBox._element_dict.values())
        for _row_index in range(self.composition_table.rowCount()):
            _Z = np.int(self.composition_table.item(_row_index, 1).text())
            _charge = np.int(self.composition_table.item(_row_index, 2).text())
            _n = np.float(self.composition_table.item(_row_index, 3).text())
            _key = str(_key_list[_val_list.index(_Z)])
            _dict_entry = {_key: [_Z, _charge, _n]}
            _composition_dict.update(_dict_entry)
        
        _n_total = sum([_composition_dict[_el][2] for _el in _composition_dict])
        for _el in _composition_dict:
            _composition_dict[_el][2] /= _n_total
            _composition_dict[_el] = tuple(_composition_dict[_el])
        return _composition_dict
    
    
    def update_mass_density(self):
        _composition = self.get_composition_dict()
        _atomic_density = np.float(self.density_input.text())
        _mass_density = core.conv_density(_atomic_density, _composition)
        self.mass_density.setText('{0:.3f}'.format(_mass_density))

class DataOptionsGroupBox(QGroupBox):
    
    def __init__(self, *args):
        super(DataOptionsGroupBox, self).__init__(*args)
        self.setTitle('Data Options')
        self.setAlignment(Qt.AlignLeft)
        self.setStyleSheet('GroupBox::title{subcontrol-origin: margin; subcontrol-position: top left;}')
        
        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()


    def create_widgets(self):
        
        self.qmax_label = QLabel('Q-Max cutoff: ')
        self.qmax_input = QLineEdit()
        self.qmax_check = QCheckBox()
        
        self.qmin_label = QLabel('Q-Min cutoff: ')
        self.qmin_input = QLineEdit()
        self.qmin_check = QCheckBox()
        
        self.smooth_label = QLabel('Smooth Data? ')
        self.smooth_data_check = QCheckBox()
        
        self.window_length_lbl = QLabel('Window size')
        self.window_length_input = QLineEdit('5')
        self.poly_order_lbl = QLabel('Poly order')
        self.poly_order_input = QLineEdit('3')
        
        
        self.mod_func_lbl = QLabel('Use modification function?')
        self.mod_func_input = QComboBox()   
        self.mod_func_input.insertItem(0, 'None')
        self.mod_func_input.insertItem(1, 'Lorch')
        self.mod_func_input.insertItem(2, 'Cosine-window')
        self.mod_func_input.setCurrentIndex(0)

        self.window_start_input = QLineEdit()
        
        self.method_button_group = QButtonGroup()
        self.al_btn = QRadioButton('Ashcroft-Langreth')
        self.fb_btn = QRadioButton('Faber-Ziman')
        self.method_button_group.addButton(self.al_btn)
        self.method_button_group.addButton(self.fb_btn)
        
        self.method_lbl = QLabel('S(Q) formulation: ')
                
        self.calc_sq_btn = QPushButton('Calc S(Q)')
        
    def style_widgets(self):  
        
        self.qmax_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.qmax_input.setAlignment(Qt.AlignRight)
        self.qmax_input.setValidator(QDoubleValidator())
        self.qmax_input.setMaximumWidth(70)
        self.qmax_input.setEnabled(False)
        self.qmax_check.setChecked(False)
        self.qmax_label.setEnabled(False)
        
        
        self.qmin_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.qmin_input.setAlignment(Qt.AlignRight)
        self.qmin_input.setValidator(QDoubleValidator())
        self.qmin_input.setMaximumWidth(70)
        self.qmin_input.setEnabled(False)
        self.qmin_check.setChecked(False)
        self.qmin_label.setEnabled(False)
        
        self.smooth_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.smooth_data_check.setChecked(False)
        
        self.window_length_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.poly_order_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.window_length_input.setMaximumWidth(70)
        self.poly_order_input.setMaximumWidth(70)
        self.window_length_input.setValidator(QIntValidator())
        self.poly_order_input.setValidator(QIntValidator())     
        
        self.window_length_lbl.setEnabled(False)
        self.window_length_input.setEnabled(False)
        self.poly_order_lbl.setEnabled(False)
        self.poly_order_input.setEnabled(False)
        
        
        self.window_start_input.setValidator(QDoubleValidator())
        self.window_start_input.setEnabled(False)
        self.al_btn.setChecked(True)
    
    def create_layout(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 10, 20, 7)
        self.main_layout.setSpacing(5)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        self.grid_layout.setColumnStretch(0, 4)
        self.grid_layout.setColumnStretch(1, 4)
        self.grid_layout.setColumnStretch(2, 2)
        
        self.grid_layout.addWidget(self.qmax_label, 0, 0)
        self.grid_layout.addWidget(self.qmax_input, 0, 1)
        self.grid_layout.addWidget(self.qmax_check, 0, 2)
        
        self.grid_layout.addWidget(self.qmin_label, 1, 0)
        self.grid_layout.addWidget(self.qmin_input, 1, 1)
        self.grid_layout.addWidget(self.qmin_check, 1, 2)        
               
        self.grid_layout.addWidget(self.smooth_label, 2, 0)
        #self.grid_layout.addWidget(QW('-'), 1, 1)
        self.grid_layout.addWidget(self.smooth_data_check, 2, 2)
        
        #self.grid_layout.addWidget(self.window_length_lbl, 3, 1)
        #self.grid_layout.addWidget(self.window_length_input, 3, 2)
        #self.grid_layout.addWidget(self.poly_order_lbl, 4, 1)
        #self.grid_layout.addWidget(self.poly_order_input, 4, 2)
        

        self.grid_layout.addWidget(self.mod_func_lbl, 3, 0, 1, 2)
        self.grid_layout.addWidget(self.mod_func_input, 4, 0, 1, 2)
        self.grid_layout.addWidget(self.window_start_input, 4, 2)
        self.grid_layout.addWidget(self.method_lbl, 5, 0)
        
        self.hbtn_layout = QHBoxLayout()
        self.hbtn_layout.addWidget(self.al_btn)
        self.hbtn_layout.addWidget(self.fb_btn)
        
        self.main_layout.addLayout(self.grid_layout)
        self.main_layout.addLayout(self.hbtn_layout)
        self.main_layout.addWidget(self.calc_sq_btn)

        self.setLayout(self.main_layout)      
     
   
    def create_signals(self):

        self.qmax_check.stateChanged.connect(self.qmax_state_changed)
        self.qmin_check.stateChanged.connect(self.qmin_state_changed)
        self.mod_func_input.currentIndexChanged.connect(self.mod_func_changed)
        
        
    def qmax_state_changed(self):
        if self.qmax_check.isChecked():
            self.qmax_input.setEnabled(True)
            self.qmax_label.setEnabled(True)
        else:
            self.qmax_input.setEnabled(False)
            self.qmax_label.setEnabled(False)
    
    def qmin_state_changed(self):
        if self.qmin_check.isChecked():
            self.qmin_input.setEnabled(True)
            self.qmin_label.setEnabled(True)
        else:
            self.qmin_input.setEnabled(False)
            self.qmin_label.setEnabled(False)
    
    def mod_func_changed(self):
        if self.mod_func_input.currentText() == 'Cosine-window':
            self.window_start_input.setEnabled(True)
        else:
            self.window_start_input.setEnabled(False)
        
class OptimOptionsGroupBox(QGroupBox):
    
    def __init__(self, *args):
        super(OptimOptionsGroupBox, self).__init__(*args)
        self.setTitle('Optimisation Options')
        self.setAlignment(Qt.AlignLeft)
        self.setStyleSheet('GroupBox::title{subcontrol-origin: margin; subcontrol-position: top left;}')
        self.setCheckable(True)
        self.setChecked(False)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        self.create_signals()


    def create_widgets(self):
        self.rmin_label = QLabel('R-Min cutoff: ')
        self.rmin_input = QLineEdit('2.3')
        #self.d_pq_label = QLabel('Atomic distances: ')
        #self.d_pq_input = QLineEdit('2.9')
        self.niter_label = QLabel('No. iterations: ')        
        self.niter_input = QLineEdit('5')
        self.opt_check = QCheckBox('Refine density? ')
        self.lb_label = QLabel('Lower bound: ')
        self.lb_input = QLineEdit()
        self.ub_label = QLabel('Upper bound: ')
        self.ub_input = QLineEdit()
        self.opt_button = QPushButton('Refine S(Q)')
        
    def style_widgets(self):
        
        self.rmin_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        #self.d_pq_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.niter_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.lb_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.ub_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

               
        self.rmin_input.setAlignment(Qt.AlignRight)
        self.rmin_input.setValidator(QDoubleValidator())
        self.rmin_input.setMaximumWidth(70)
        self.rmin_input.setToolTip('Intramolecular distance cut-off')
        self.rmin_label.setToolTip('Intramolecular distance cut-off')

        
        #self.d_pq_input.setAlignment(Qt.AlignRight)
        #self.d_pq_input.setValidator(QDoubleValidator())
        #self.d_pq_input.setMaximumWidth(70)
        #self.d_pq_input.setToolTip('Inter-atomic distances for modelled behaviour')
        #self.d_pq_label.setToolTip('Inter-atomic distances for modelled behaviour')

        self.niter_input.setAlignment(Qt.AlignRight)
        self.niter_input.setValidator(QIntValidator())
        self.niter_input.setMaximumWidth(70)

        self.lb_input.setAlignment(Qt.AlignRight)
        self.lb_input.setValidator(QDoubleValidator())
        self.lb_input.setMaximumWidth(70)

        self.ub_input.setAlignment(Qt.AlignRight)
        self.ub_input.setValidator(QDoubleValidator())
        self.ub_input.setMaximumWidth(70)        
        
        self.opt_check.setChecked(False)
        
        self.lb_label.setEnabled(False)
        self.lb_input.setEnabled(False)
        self.ub_label.setEnabled(False)
        self.ub_input.setEnabled(False)
       
    def create_layout(self):
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 10, 20, 7)
        self.main_layout.setSpacing(25)


        self.top_grid = QGridLayout()
        self.top_grid.setSpacing(15)
        #self.grid_layout.setColumnStretch(0, 4)
        #self.grid_layout.setColumnStretch(1, 4)
        #self.grid_layout.setColumnStretch(2, 2)
        self.top_grid.addWidget(self.rmin_label, 0, 0)
        self.top_grid.addWidget(self.rmin_input, 0, 1)
        #self.top_grid.addWidget(self.d_pq_label, 1, 0)
        #self.top_grid.addWidget(self.d_pq_input, 1, 1)
        self.top_grid.addWidget(self.niter_label, 1, 0)
        self.top_grid.addWidget(self.niter_input, 1, 1)
        
        self.bottom_grid = QGridLayout()
        self.bottom_grid.setSpacing(15)
        self.bottom_grid.addWidget(self.opt_check, 0, 0)
        self.bottom_grid.addWidget(self.lb_label, 1, 0)
        self.bottom_grid.addWidget(self.lb_input, 1, 1)
        self.bottom_grid.addWidget(self.ub_label, 2, 0)
        self.bottom_grid.addWidget(self.ub_input, 2, 1)

        self.main_layout.addLayout(self.top_grid)
        self.main_layout.addLayout(self.bottom_grid)
        self.main_layout.addWidget(self.opt_button)

        self.setLayout(self.main_layout)      
        
    def create_signals(self):
        self.opt_check.stateChanged.connect(self.opt_state_changed)
        
        
    def opt_state_changed(self):
        if self.opt_check.isChecked():
            self.lb_input.setEnabled(True)
            self.lb_label.setEnabled(True)
            self.ub_input.setEnabled(True)
            self.ub_label.setEnabled(True)
        else:
            self.lb_input.setEnabled(False)
            self.lb_label.setEnabled(False)
            self.ub_input.setEnabled(False)
            self.ub_label.setEnabled(False)
        
                
class OptimResultsGroupBox(QGroupBox):
    
    def __init__(self, *args):
        super(OptimResultsGroupBox, self).__init__(*args)
        self.setTitle('Results')
        self.setAlignment(Qt.AlignLeft)
        self.setStyleSheet('GroupBox::title{subcontrol-origin: margin; subcontrol-position: top left;}')
        self.setEnabled(False)

        self.create_widgets()
        self.style_widgets()
        self.create_layout()
        #self.create_signals()


    def create_widgets(self):
        
        self.chi_sq_label = QLabel('Final Chi-squared: ')
        self.chi_sq_output = QLineEdit()
        
        self.density_output_label = QLabel('Refined density (at/A<sup>3</sup>): ')
        self.density_output = QLineEdit()
        
        self.mass_density_label = QLabel('(g/cm<sup>3</sup>): ')
        self.mass_density = QLineEdit()
        
    def style_widgets(self):
        
        self.chi_sq_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.density_output_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.mass_density_label.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        self.chi_sq_output.isReadOnly()
        self.density_output.isReadOnly()
        self.mass_density.isReadOnly()
        self.chi_sq_output.setMaximumWidth(82)
        self.density_output.setMaximumWidth(82)
        self.mass_density.setMaximumWidth(82)
        
        self.density_output.setEnabled(False)
        self.density_output_label.setEnabled(False)
        self.mass_density.setEnabled(False)
        self.mass_density_label.setEnabled(False)
        
        self.density_output.setReadOnly(True)
        self.chi_sq_output.setReadOnly(True)
        self.mass_density.setReadOnly(True)

    def create_layout(self):
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 10, 20, 7)
        self.main_layout.setSpacing(25)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        
        self.grid_layout.addWidget(self.chi_sq_label, 0, 0)
        self.grid_layout.addWidget(self.chi_sq_output, 0, 1)
        self.grid_layout.addWidget(self.density_output_label, 1, 0)
        self.grid_layout.addWidget(self.density_output, 1, 1)
        self.grid_layout.addWidget(self.mass_density_label, 2, 0)
        self.grid_layout.addWidget(self.mass_density, 2, 1)
        
        self.main_layout.addLayout(self.grid_layout)
        
        self.setLayout(self.main_layout)

