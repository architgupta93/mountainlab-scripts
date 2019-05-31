"""
Qt Application for running MountainSort and visualizing sorted clusters.
"""
# Sysyem imports
import os
import sys
import json
import numpy as np
from mountainlab_pytools import mdaio
from sklearn.preprocessing import normalize
from scipy.signal import butter, lfilter

# Qt5 imports
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QDialog, QFileDialog, QMessageBox
from PyQt5.QtWidgets import QPushButton, QSlider, QRadioButton, QLabel, QInputDialog
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QGridLayout, QComboBox

# Matplotlib in Qt5
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.cm as colormap
from matplotlib import gridspec
from matplotlib.animation import FuncAnimation

# Local imports
import MountainViewIO
import QtHelperUtils

MODULE_IDENTIFIER = "[MLView] "
FIRING_CLIP_SIZE = 50
N_ELECTRODE_CHANNELS = 4

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a


def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

class MLViewer(QMainWindow):

    """Docstring for MLViewer. """

    def __init__(self, args):
        """TODO: to be defined1. """
        QMainWindow.__init__(self)
        self.setWindowTitle('Cluster viewer')
        self.statusBar().showMessage('Load or create firings file from File Menu.')
        self.setupMenus()

        # Tetrode info fields
        self.n_units = 0
        self.n_tetrodes = 0

        # General info
        if args.data_dir:
            self.data_dir = args.data_dir
        else:
            self.data_dir = None

        if args.raw:
            self.raw_data_location = args.raw
        else:
            self.raw_data_location = None

        # Data entries
        self.firing_data = None
        self.firing_clips = None
        self.firing_amplitudes = None
        self.clusters = None
        self.current_tetrode = 0

        # Graphical entities
        self.widget  = QDialog()
        self.figure  = Figure(figsize=(12,12))
        self.canvas  = FigureCanvas(self.figure)
        plot_grid    = gridspec.GridSpec(3, 2)
        self.toolbar = NavigationToolbar(self.canvas, self.widget)

        self._ax_ch1v2 = self.figure.add_subplot(plot_grid[0])
        self._ax_ch1v3 = self.figure.add_subplot(plot_grid[1])
        self._ax_ch1v4 = self.figure.add_subplot(plot_grid[2])
        self._ax_ch2v3 = self.figure.add_subplot(plot_grid[3])
        self._ax_ch2v4 = self.figure.add_subplot(plot_grid[4])
        self._ax_ch3v4 = self.figure.add_subplot(plot_grid[5])

        self.unit_selection = QComboBox()
        # self.unit_selection.currentIndexChanged.connect(self.refresh)
        # Add next and prev buttons to look at individual cells.
        self.next_unit_button = QPushButton('Next')
        self.next_unit_button.clicked.connect(self.NextUnit)
        self.prev_unit_button = QPushButton('Prev')
        self.prev_unit_button.clicked.connect(self.PrevUnit)

        # Selecting individual tetrodes
        self.tetrode_selection = QComboBox()
        # self.tetrode_selection.currentIndexChanged.connect(self.refresh)
        # Add next and prev buttons to look at individual cells.
        self.next_tet_button = QPushButton('Next')
        self.next_tet_button.clicked.connect(self.NextTetrode)
        self.prev_tet_button = QPushButton('Prev')
        self.prev_tet_button.clicked.connect(self.PrevTetrode)

        # Launch the main graphical interface as a widget
        self.setupWidgetLayout()
        self.setCentralWidget(self.widget)
        self.setGeometry(100, 100, 1200, 1200)
        self.clearAxes()

    def clearAxes(self):
        self._ax_ch1v2.cla()
        self._ax_ch1v2.grid(True)
        self._ax_ch1v2.set_xlim((-500, 1500))
        self._ax_ch1v2.set_ylim((-500, 1500))

        self._ax_ch1v3.cla()
        self._ax_ch1v3.grid(True)
        self._ax_ch1v3.set_xlim((-500, 1500))
        self._ax_ch1v3.set_ylim((-500, 1500))

        self._ax_ch1v4.cla()
        self._ax_ch1v4.grid(True)
        self._ax_ch1v4.set_xlim((-500, 1500))
        self._ax_ch1v4.set_ylim((-500, 1500))

        self._ax_ch2v3.cla()
        self._ax_ch2v3.grid(True)
        self._ax_ch2v3.set_xlim((-500, 1500))
        self._ax_ch2v3.set_ylim((-500, 1500))

        self._ax_ch2v4.cla()
        self._ax_ch2v4.grid(True)
        self._ax_ch2v4.set_xlim((-500, 1500))
        self._ax_ch2v4.set_ylim((-500, 1500))
 
        self._ax_ch3v4.cla()
        self._ax_ch3v4.grid(True)
        self._ax_ch3v4.set_xlim((-500, 1500))
        self._ax_ch3v4.set_ylim((-500, 1500))

    def setupWidgetLayout(self):
        parent_layout_box = QVBoxLayout()
        parent_layout_box.addWidget(self.toolbar)
        parent_layout_box.addWidget(self.canvas)
        parent_layout_box.addStretch(1)

        # Controls for looking at individual units and tetrodes
        # TODO: Add labels differentiating units and tetrodes.
        vbox_unit_selection = QVBoxLayout()
        vbox_unit_selection.addWidget(self.unit_selection)
        vbox_unit_selection.addWidget(self.next_unit_button)
        vbox_unit_selection.addWidget(self.prev_unit_button)
        vbox_unit_selection.addStretch(1)

        vbox_tet_selection = QVBoxLayout()
        vbox_tet_selection.addWidget(self.tetrode_selection)
        vbox_tet_selection.addWidget(self.next_tet_button)
        vbox_tet_selection.addWidget(self.prev_tet_button)
        vbox_tet_selection.addStretch(1)

        # Add Horizontal button groups here
        hbox_control_buttons = QHBoxLayout()
        hbox_control_buttons.addStretch(1)
        hbox_control_buttons.addLayout(vbox_unit_selection)
        hbox_control_buttons.addLayout(vbox_tet_selection)

        parent_layout_box.addLayout(hbox_control_buttons)
        QDialog.setLayout(self.widget, parent_layout_box)

    def disconnectAndQuit(self):
        qApp.quit()

    def refresh(self, _):
        """
        Redraw the axes with current firing data.
        """
        self.clearAxes()
        for cl_id in self.clusters:
            spikes_in_cluster = self.firing_data[2] == cl_id
            # These are the 2D plots
            self._ax_ch1v2.scatter(self.firing_amplitudes[spikes_in_cluster,0], self.firing_amplitudes[spikes_in_cluster,1], s=8)
            self._ax_ch1v3.scatter(self.firing_amplitudes[spikes_in_cluster,0], self.firing_amplitudes[spikes_in_cluster,2], s=8)
            self._ax_ch1v4.scatter(self.firing_amplitudes[spikes_in_cluster,0], self.firing_amplitudes[spikes_in_cluster,3], s=8)
            self._ax_ch2v3.scatter(self.firing_amplitudes[spikes_in_cluster,1], self.firing_amplitudes[spikes_in_cluster,2], s=8)
            self._ax_ch2v4.scatter(self.firing_amplitudes[spikes_in_cluster,1], self.firing_amplitudes[spikes_in_cluster,3], s=8)
            self._ax_ch3v4.scatter(self.firing_amplitudes[spikes_in_cluster,2], self.firing_amplitudes[spikes_in_cluster,3], s=8)
        self.canvas.draw()

    def extractClips(self, _, clips_file=None):
        """
        Extract clips (spike waveforms on all the 4 channels for a given tetrode.)
        """

        if self.firing_data is None:
            QtHelperUtils.display_warning('Load firings data first!')
            return

        if clips_file is None:
            clips_file = QtHelperUtils.get_open_file_name(data_dir=self.raw_data_location,\
                    file_format='MDA (*.mda)', message='Choose raw file')

        try:
            # raw_clip_data = normalize(mdaio.readmda(clips_file), axis=1)
            # raw_clip_data = mdaio.readmda(clips_file)
            raw_clip_data = butter_bandpass_filter(mdaio.readmda(clips_file), 300, 6000, \
                    MountainViewIO.SPIKE_SAMPLING_RATE)
        except (FileNotFoundError, IOError) as err:
            QtHelperUtils.display_warning('Unable to read MDA file.')
            return

        # Try reading the timestamps from the same location... Usually, data
        # file is stored alongside the timestamp file.
        timestamp_file = clips_file.split('.nt')[0] + '.timestamps.mda'
        if not os.path.exists(timestamp_file):
            timestamp_file = QtHelperUtils.get_open_file_name(data_dir=self.raw_data_location,\
                    file_format='MDA (*.mda)', message='Choose timestamps file') 

        try:
            spike_timestamps = mdaio.readmda(timestamp_file)
        except (FileNotFoundError, IOError) as err:
            QtHelperUtils.display_warning('Unable to read timestamps file.')
            return

        n_spikes = len(self.firing_data[1])
        self.firing_clips = np.empty((n_spikes, N_ELECTRODE_CHANNELS, \
                FIRING_CLIP_SIZE+FIRING_CLIP_SIZE), dtype=float)
        self.firing_amplitudes = np.empty((n_spikes, N_ELECTRODE_CHANNELS), \
                dtype=float)


        # Find the firing timepoint in the raw data file. If the firings data
        # is raw data from mountainsort, then you have the indices readily
        # available to you. Otherwise, need to search for clips in the raw data
        # file by timestamp.
        spike_indices = np.searchsorted(spike_timestamps, self.firing_data[1])
        for spk_idx in range(n_spikes):
            if (spike_indices[spk_idx] < FIRING_CLIP_SIZE) or (spike_indices[spk_idx]+FIRING_CLIP_SIZE>len(spike_timestamps)):
                # Unable to get the complete clip for this spike, might as well
                # ignore it... This shouldn't be so common though!
                self.firing_clips[spk_idx, :, :] = 0.0
                self.firing_amplitudes[spk_idx, :] = 0.0
                print(MODULE_IDENTIFIER + 'WARNING: Unable to read spike clip in data')
                continue
            self.firing_clips[spk_idx, :, :] = raw_clip_data[:,spike_indices[spk_idx]-FIRING_CLIP_SIZE:spike_indices[spk_idx]+FIRING_CLIP_SIZE]
            if (raw_clip_data[:,spike_indices[spk_idx]] < 0.0).any():
                self.firing_amplitudes[spk_idx,:] = -raw_clip_data[:,spike_indices[spk_idx]]
            else:
                self.firing_data[2][spk_idx] = -1
                self.firing_amplitudes[spk_idx,:] = 0.0

        # Raw data has negative spike amplitudes which need to be corrected.
        # self.firing_amplitudes = -np.min(self.firing_clips, axis=2)

        print(self.firing_amplitudes.shape)
        self.statusBar().showMessage(str(n_spikes) + ' firing clips loaded from ' + clips_file)

    def loadFirings(self, _, firings_filename=None):
        """
        Load raw or clustered firings from file.
        """
        if firings_filename is None:
            firings_filename = QtHelperUtils.get_open_file_name(data_dir=self.data_dir,\
                    file_format='MDA (*.mda)', message='Choose firings file')
        try:
            self.firing_data = mdaio.readmda(firings_filename)
            self.clusters = set(self.firing_data[2])
        except (FileNotFoundError, IOError) as err:
            QtHelperUtils.display_warning('Unable to read MDA file.')
            return

        """
        curation_file_path = os.path.join(os.path.dirname(firings_filename), 'hand_curated.mv2')
        try:
            # Read the curation file for info on spike clusters
            with open(curation_file_path, 'r') as f:
                curation_file = json.load(f)
            # Get all cluster IDs. This includes noise, mua, everything!
            self.clusters = list()
            for cl in curation_file['cluster_attributes'].keys():
                if 'accepted' in curation_file['cluster_attributes'][cl]['tags']:
                    self.clusters.append(int(cl))
        except (FileNotFoundError, IOError) as err:
            print(MODULE_IDENTIFIER + 'Unable to read curation file.')
            self.clusters = set(self.firing_data[2])
        """

        self.statusBar().showMessage('Firing data loaded from ' + firings_filename)

    def loadClusterFile(self, _):
        """
        Load up a previously saved cluster-metrics file.
        """
        pass

    def NextUnit(self):
        QtHelperUtils.display_warning('Function not implemented!')

    def PrevUnit(self):
        QtHelperUtils.display_warning('Function not implemented!')

    def NextTetrode(self):
        QtHelperUtils.display_warning('Function not implemented!')

    def PrevTetrode(self):
        QtHelperUtils.display_warning('Function not implemented!')

    def setupMenus(self):
        # Set up the menu bar
        menu_bar = self.menuBar()

        # File menu - Save, Load (Processed Data), Quit
        file_menu = menu_bar.addMenu('&File')
        refresh_action = file_menu.addAction('&Refresh')
        refresh_action.setShortcut('Ctrl+R')
        refresh_action.triggered.connect(self.refresh)

        # =============== SAVE MENU =============== 
        save_menu = file_menu.addMenu('&Save')

        # =============== LOAD MENU =============== 
        open_menu = file_menu.addMenu('&Load')
        load_firings_action = open_menu.addAction('&Firings')
        load_firings_action.setShortcut('Ctrl+F')
        load_firings_action.triggered.connect(self.loadFirings)

        load_clusters_action = open_menu.addAction('&Clusters')
        load_clusters_action.setShortcut('Ctrl+C')
        load_clusters_action.triggered.connect(self.loadClusterFile)

        load_clips_action = open_menu.addAction('C&lips')
        load_clips_action.setShortcut('Ctrl+L')
        load_clips_action.triggered.connect(self.extractClips)

        quit_action = file_menu.addAction('&Exit')
        quit_action.setShortcut('Ctrl+Q')
        quit_action.setStatusTip('Exit Program')
        quit_action.triggered.connect(self.disconnectAndQuit)

        # =============== PLOT MENU =============== 
        plot_menu = menu_bar.addMenu('&Plot')

        # =============== PREF MENU =============== 
        preferences_menu = menu_bar.addMenu('&Preferences')
        
def launchMLViewApplication(args):
    """
    Launch the main Spike Analysis application using the SAMainWindow class

    :args: Arguments to be passed into the class
    """

    qt_args = list()
    qt_args.append(args[0])
    qt_args.append('-style')
    qt_args.append('Windows')
    print(MODULE_IDENTIFIER + "Qt Arguments: " + str(qt_args))
    app = QApplication(qt_args)
    print(MODULE_IDENTIFIER + "Parsing Input Arguments: " + str(sys.argv))

    parsed_arguments = QtHelperUtils.parseQtCommandlineArgs(args)
    sa_window = MLViewer(parsed_arguments)
    sa_window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
        launchMLViewApplication(sys.argv)
