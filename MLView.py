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
from sklearn.decomposition import PCA
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
import MS4batch
import MountainViewIO
import QtHelperUtils

MODULE_IDENTIFIER = "[MLView] "
FIRING_CLIP_SIZE = 32
FIRING_PRE_CLIP = 8
FIRING_POST_CLIP = FIRING_CLIP_SIZE - FIRING_PRE_CLIP
ACCESS_TIMESTAMPED_FIRINGS = False
N_ELECTRODE_CHANNELS = 4
WHITEN_CLIP_DATA = False

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
        self.setWindowTitle('Mountainsort Helper/Viewer')
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

        if args.output_dir:
            self.output_dir = args.output_dir
        else:
            print(MODULE_IDENTIFIER + 'Output directory not specified. Using current directory.')
            self.output_dir = os.getcwd()

        if args.raw:
            self.raw_data_location = args.raw
        else:
            self.raw_data_location = None

        # Data entries
        self.firing_data = None
        self.firing_clips = None
        self.firing_amplitudes = None
        self.currently_selected_clusters = None
        self.clusters = None
        self.cluster_names = None
        self.cluster_colors = None
        self.current_tetrode = 0
        self.firing_limits = (-500, 3000)
        self.session_id = 1
        self.timestamp_file = None
        self.timestamp_data = None

        # Graphical entities
        self.widget  = QDialog()
        self.figure  = Figure(figsize=(12,12))
        self.canvas  = FigureCanvas(self.figure)
        plot_grid    = gridspec.GridSpec(2, 3)
        self.toolbar = NavigationToolbar(self.canvas, self.widget)

        self._ax_ch1v2 = self.figure.add_subplot(plot_grid[0])
        self._ax_ch1v3 = self.figure.add_subplot(plot_grid[1])
        self._ax_ch1v4 = self.figure.add_subplot(plot_grid[2])
        self._ax_ch2v3 = self.figure.add_subplot(plot_grid[3])
        self._ax_ch2v4 = self.figure.add_subplot(plot_grid[4])
        self._ax_ch3v4 = self.figure.add_subplot(plot_grid[5])

        self.unit_selection = QComboBox()
        self.unit_selection.activated.connect(self.refresh)
        # Add next and prev buttons to look at individual cells.
        self.next_unit_button = QPushButton('Next')
        self.next_unit_button.clicked.connect(self.NextUnit)
        self.prev_unit_button = QPushButton('Prev')
        self.prev_unit_button.clicked.connect(self.PrevUnit)

        # Selecting individual tetrodes
        self.tetrode_selection = QComboBox()
        self.tetrode_selection.activated.connect(self.fetchTetrodeData)
        # Add next and prev buttons to look at individual cells.
        self.next_tet_button = QPushButton('Next')
        self.next_tet_button.clicked.connect(self.NextTetrode)
        self.prev_tet_button = QPushButton('Prev')
        self.prev_tet_button.clicked.connect(self.PrevTetrode)

        # Launch the main graphical interface as a widget
        self.show_cluster_widget = False
        self.setGeometry(100, 100, 400, 20)

        if self.data_dir is not None:
            self.populateTetrodeMenu()

    def showCluterWidget(self):
        self.show_cluster_widget = True
        self.setupWidgetLayout()
        self.setCentralWidget(self.widget)
        self.setGeometry(100, 100, 1000, 750)
        self.clearAxes()

    def clearAxes(self):
        if not self.show_cluster_widget:
            return

        self._ax_ch1v2.cla()
        self._ax_ch1v2.grid(True)
        self._ax_ch1v2.set_xlim(self.firing_limits)
        self._ax_ch1v2.set_ylim(self.firing_limits)
        self._ax_ch1v2.set_xticks([])
        self._ax_ch1v2.set_yticks([])

        self._ax_ch1v3.cla()
        self._ax_ch1v3.grid(True)
        self._ax_ch1v3.set_xlim(self.firing_limits)
        self._ax_ch1v3.set_ylim(self.firing_limits)
        self._ax_ch1v3.set_xticks([])
        self._ax_ch1v3.set_yticks([])

        self._ax_ch1v4.cla()
        self._ax_ch1v4.grid(True)
        self._ax_ch1v4.set_xlim(self.firing_limits)
        self._ax_ch1v4.set_ylim(self.firing_limits)
        self._ax_ch1v4.set_xticks([])
        self._ax_ch1v4.set_yticks([])

        self._ax_ch2v3.cla()
        self._ax_ch2v3.grid(True)
        self._ax_ch2v3.set_xlim(self.firing_limits)
        self._ax_ch2v3.set_ylim(self.firing_limits)
        self._ax_ch2v3.set_xticks([])
        self._ax_ch2v3.set_yticks([])

        self._ax_ch2v4.cla()
        self._ax_ch2v4.grid(True)
        self._ax_ch2v4.set_xlim(self.firing_limits)
        self._ax_ch2v4.set_ylim(self.firing_limits)
        self._ax_ch2v4.set_xticks([])
        self._ax_ch2v4.set_yticks([])
 
        self._ax_ch3v4.cla()
        self._ax_ch3v4.grid(True)
        self._ax_ch3v4.set_xlim(self.firing_limits)
        self._ax_ch3v4.set_ylim(self.firing_limits)
        self._ax_ch3v4.set_xticks([])
        self._ax_ch3v4.set_yticks([])

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
        if not self.show_cluster_widget:
            return

        self.clearAxes()
        for cl_id in self.currently_selected_clusters:
            spikes_in_cluster = self.clusters[cl_id]
            # print(spikes_in_cluster)

            # These are the 2D plots
            self._ax_ch1v2.scatter(self.firing_amplitudes[spikes_in_cluster,0], self.firing_amplitudes[spikes_in_cluster,1], s=2)
            self._ax_ch1v3.scatter(self.firing_amplitudes[spikes_in_cluster,0], self.firing_amplitudes[spikes_in_cluster,2], s=2)
            self._ax_ch1v4.scatter(self.firing_amplitudes[spikes_in_cluster,0], self.firing_amplitudes[spikes_in_cluster,3], s=2)
            self._ax_ch2v3.scatter(self.firing_amplitudes[spikes_in_cluster,1], self.firing_amplitudes[spikes_in_cluster,2], s=2)
            self._ax_ch2v4.scatter(self.firing_amplitudes[spikes_in_cluster,1], self.firing_amplitudes[spikes_in_cluster,3], s=2)
            self._ax_ch3v4.scatter(self.firing_amplitudes[spikes_in_cluster,2], self.firing_amplitudes[spikes_in_cluster,3], s=2)
        self.canvas.draw()

    def fetchTetrodeData(self, _):
        """
        Fetch spikes and clips/whitened data for the current tetrode and display it.
        """
        tetrode_id = self.tetrode_selection.currentText()
        if self.output_dir is None:
            self.output_dir = QtHelperUtils.get_directory(message="Choose firings data directory.")
        tetrode_dir = os.path.join(self.output_dir, 'nt' + tetrode_id)
        if ACCESS_TIMESTAMPED_FIRINGS:
            firings_file = 'firings-' + str(self.session_id) + '.curated.mda'
        else:
            firings_file = 'firings.curated.mda'
        firings_file_path = os.path.join(tetrode_dir, firings_file)

        if not os.path.exists(firings_file_path):
            QtHelperUtils.display_warning('Firings file not found for tetrode %s.'%tetrode_id)
            return

        # Get the spike data
        self.loadFirings(False, firings_file_path)
        
        # Get the clips data
        # TODO: This approach only works for getting the raw data. For whitened
        # data, other stuff might be needed.
        if self.raw_data_location is None:
            self.raw_data_location = QtHelperUtils.get_directory(message="Choose raw data location.")

        # Try to get the clips file first
        clips_file_path = None
        all_raw_files = os.listdir(self.raw_data_location)
        tetrode_identifier = 'nt'+str(tetrode_id)+'.mda'
        for raw_file in all_raw_files:
            if tetrode_identifier in raw_file:
                clips_file_path = os.path.join(self.raw_data_location, raw_file)
                self.statusBar().showMessage('Found clips file: ' + clips_file_path)
                break
        self.extractClips(False, clips_file_path)
        self.refresh(False)

    def extractWhitened(self, _, clips_file=None):
        """
        Extract clips from whitened data and use that to get firing information.
        """

        if self.firing_data is None:
            QtHelperUtils.display_warning('Load firings data first!')
            return

        if clips_file is None:
            clips_file = QtHelperUtils.get_open_file_name(data_dir=self.raw_data_location,\
                    file_format='MDA (*.mda)', message='Choose whitened data file')

        self.firing_limits = (-20, 20)
        pass

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
            filtered_clip_data = butter_bandpass_filter(mdaio.readmda(clips_file), 600, 6000, \
                    MountainViewIO.SPIKE_SAMPLING_RATE)
            print(MODULE_IDENTIFIER + 'Filtered clip data...')
            if WHITEN_CLIP_DATA:
                pca_filter = PCA(whiten=True)
                raw_clip_data = np.matmul(pca_filter.fit_transform(filtered_clip_data).T, filtered_clip_data)
                print(MODULE_IDENTIFIER + 'Whitened clip data...')
            else:
                raw_clip_data = filtered_clip_data
        except (FileNotFoundError, IOError) as err:
            QtHelperUtils.display_warning('Unable to read MDA file.')
            return

        # Try reading the timestamps from the same location... Usually, data
        # file is stored alongside the timestamp file.
        if self.timestamp_data is None:
            timestamp_file = clips_file.split('.nt')[0] + '.timestamps.mda'
            if not os.path.exists(timestamp_file):
                timestamp_file = QtHelperUtils.get_open_file_name(data_dir=self.raw_data_location,\
                        file_format='MDA (*.mda)', message='Choose timestamps file') 

            try:
                self.timestamp_data = mdaio.readmda(timestamp_file)
            except (FileNotFoundError, IOError) as err:
                QtHelperUtils.display_warning('Unable to read timestamps file.')
                return

        n_spikes = len(self.firing_data[1])
        self.firing_clips = np.empty((n_spikes, N_ELECTRODE_CHANNELS, \
                FIRING_CLIP_SIZE), dtype=float)
        self.firing_amplitudes = np.empty((n_spikes, N_ELECTRODE_CHANNELS), \
                dtype=float)

        # Find the firing timepoint in the raw data file. If the firings data
        # is raw data from mountainsort, then you have the indices readily
        # available to you. Otherwise, need to search for clips in the raw data
        # file by timestamp.
        if ACCESS_TIMESTAMPED_FIRINGS:
            spike_indices = np.searchsorted(self.timestamp_data, self.firing_data[1])
        else:
            spike_indices = np.array(self.firing_data[1], dtype='int')
            # print(spike_indices)


        for spk_idx in range(n_spikes):
            if (spike_indices[spk_idx] < FIRING_PRE_CLIP) or (spike_indices[spk_idx]+FIRING_POST_CLIP>len(self.timestamp_data)):
                # Unable to get the complete clip for this spike, might as well
                # ignore it... This shouldn't be so common though!
                self.firing_clips[spk_idx, :, :] = 0.0
                self.firing_amplitudes[spk_idx, :] = 0.0
                print(MODULE_IDENTIFIER + 'WARNING: Unable to read spike clip in data')
                continue
            self.firing_clips[spk_idx, :, :] = raw_clip_data[:,spike_indices[spk_idx]-FIRING_PRE_CLIP:spike_indices[spk_idx]+FIRING_POST_CLIP]
            # Raw data has negative spike amplitudes which need to be corrected.
            # self.firing_amplitudes = np.max(self.firing_clips, axis=2)

            # The index we get here will be for the spike peak in the entrie
            # 4 x clip data. We need to convert it into a (channel,sample_value)
            peak_amplitude_idx = np.argmin(self.firing_clips[spk_idx,:,:])
            peak_sample_loc    = np.unravel_index(peak_amplitude_idx, (N_ELECTRODE_CHANNELS, FIRING_CLIP_SIZE))
            self.firing_amplitudes[spk_idx,:] = -self.firing_clips[spk_idx,:,peak_sample_loc[1]]

        for example_idx in range(100,200):
            plt.subplot(221)
            plt.plot(self.firing_clips[example_idx,0,:])

            plt.subplot(222)
            plt.plot(self.firing_clips[example_idx,1,:])

            plt.subplot(223)
            plt.plot(self.firing_clips[example_idx,2,:])

            plt.subplot(224)
            plt.plot(self.firing_clips[example_idx,3,:])
            plt.show()

        print(self.firing_amplitudes.shape)
        self.firing_limits = (-500, 3000)
        # self.firing_limits = (np.min(self.firing_amplitudes), np.max(self.firing_amplitudes))
        self.statusBar().showMessage(str(n_spikes) + ' firing clips loaded from ' + clips_file)
        del raw_clip_data

    def populateTetrodeMenu(self, default_entry=None):
        try:
            self.tetrode_selection.clear()
            if self.tetrode_selection.count() == 0:
                # Populate the tetrode list using the directory found here
                tetrode_list = os.listdir(self.data_dir)
                for tet_dir in tetrode_list:
                    if 'nt' in tet_dir:
                        self.tetrode_selection.addItem(tet_dir.split('nt')[-1])
            if default_entry is not None:
                self.tetrode_selection.setCurrentIndex(self.tetrode_selection.findText(default_entry))
        except Exception as err:
            print(err)

    def populateUnitMenu(self):
        self.unit_selection.clear()
        for cl in self.cluster_names:
            self.unit_selection.addItem(str(cl))

    def getCurrentClusterSelection(self):
        if self.clusters is None:
            return

        default_selection_choice = list()
        processing_args = list()
        for cl_id in self.cluster_names:
            processing_args.append(str(cl_id))

            # Retain the previously selected clusters so that the user does not
            # have to remember them
            if self.currently_selected_clusters is None:
                default_selection_choice.append(True)
            else:
                default_selection_choice.append(cl_id in self.currently_selected_clusters)

        user_choices = QtHelperUtils.CheckBoxWidget(processing_args, message="Select clusters to view").exec_()
        if user_choices[0] == QDialog.Accepted:
            if self.currently_selected_clusters is not None:
                self.currently_selected_clusters.clear()
            else:
                self.currently_selected_clusters = list()

            print(user_choices[1])
            print(self.cluster_names)
            for accepted_idx in user_choices[1]:
                self.currently_selected_clusters.append(self.cluster_names[accepted_idx])

    def loadFirings(self, _, firings_filename=None):
        """
        Load raw or clustered firings from file.
        """
        if firings_filename is None:
            firings_filename = QtHelperUtils.get_open_file_name(data_dir=self.data_dir,\
                    file_format='MDA (*.mda)', message='Choose firings file')
            tetrode_dir = os.path.dirname(firings_filename)
            current_tetrode = tetrode_dir.split('nt')[-1]
            if self.output_dir is None:
                # Data directory is 2 levels above the firings file!
                self.output_dir = os.path.dirname(tetrode_dir)
            self.populateTetrodeMenu(current_tetrode)
        try:
            self.firing_data = mdaio.readmda(firings_filename)
            self.cluster_names = list()
            self.clusters = dict()
            for spike_idx, spike_data in enumerate(np.array(self.firing_data[2], dtype='int')):
                if spike_data not in self.clusters:
                    self.cluster_names.append(spike_data)
                    self.clusters[spike_data] = list()
                self.clusters[spike_data].append(spike_idx)

            # Assign unique color to each cluster so that the values do not
            # change as you add or remove them

            # By default set all clusters to be viewable
            self.getCurrentClusterSelection()
            self.populateUnitMenu()
        except (FileNotFoundError, IOError) as err:
            QtHelperUtils.display_warning('Unable to read MDA file.')
            return

        if not self.show_cluster_widget:
            self.showCluterWidget()
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
        current_tetrode_idx = self.tetrode_selection.currentIndex()
        if current_tetrode_idx < self.tetrode_selection.count()-1:
            self.tetrode_selection.setCurrentIndex(current_tetrode_idx+1)
            self.fetchTetrodeData(False)

    def PrevTetrode(self):
        current_tetrode_idx = self.tetrode_selection.currentIndex()
        if current_tetrode_idx > 0:
            self.tetrode_selection.setCurrentIndex(current_tetrode_idx-1)
            self.fetchTetrodeData(False)

    def getSortOptions(self):
        """
        Ask for sorting options from the user.
        """
        QtHelperUtils.display_warning('Function not implemented!')

    def sortSingleSession(self):
        """
        Sort data from a single recording session.
        """
        epoch_mda_file = QtHelperUtils.get_directory(self.data_dir, \
                message="Select epoch MDA to be sorted")
        if not epoch_mda_file:
            QtHelperUtils.display_warning('Inappropriate MDA specified for sorting!')
            return

        tetrode_range = range(1,65)
        do_mask_artifacts = True
        clear_files = True
        MS4batch.run_pipeline([epoch_mda_file], self.output_dir, tetrode_range, do_mask_artifacts, clear_files)

    def sortMultiSession(self):
        """
        Merge and sort data from multiple recording sessions.
        """
        # Get a list of MDAs to be sorted.
        mda_list = list()
        while True:
            new_mda_dir = QtHelperUtils.get_directory(self.data_dir, \
                    message="Select MDA Files (Cancel to stop)")
            if not new_mda_dir:
                break
            mda_list.append(new_mda_dir)
            print("Added %s."%new_mda_dir)

        if not mda_list:
            QtHelperUtils.display_warning('Inappropriate MDA(s) specified for sorting!')
            return

        # TODO: Create an input dialog that gets all these properties from the
        # user (dialog can also show all the directories that have been selected.)
        tetrode_range = range(1,40)
        do_mask_artifacts = True
        clear_files = True
        MS4batch.run_pipeline(mda_list, self.output_dir, tetrode_range, do_mask_artifacts, clear_files)

    def launchMountainView(self):
        """
        Launch mountain-view to look at the current tetrode's data there.
        """
        QtHelperUtils.display_warning('Function not implemented!')

    def selectOutputDirectory(self):
        """
        Select a new output directory.
        """
        self.output_dir = QtHelperUtils.get_directory(message='Select output directory.')

    def selectDataDirectory(self):
        """
        Select a new output directory.
        """
        self.data_dir = QtHelperUtils.get_directory(message='Select (processed) data directory.')

    def selectRawDirectory(self):
        """
        Select a new output directory.
        """
        self.raw_data_dir = QtHelperUtils.get_directory(message='Select (raw) data directory.')

    def setupMenus(self):
        # Set up the menu bar
        menu_bar = self.menuBar()

        # File menu - Save, Load (Processed Data), Quit
        file_menu = menu_bar.addMenu('&File')
        refresh_action = file_menu.addAction('&Refresh')
        refresh_action.setShortcut('Ctrl+R')
        refresh_action.triggered.connect(self.refresh)

        # Run Qt-Mountainview from here
        qt_mview_action = file_menu.addAction('&MountainView')
        qt_mview_action.setShortcut('Ctrl+M')
        qt_mview_action.triggered.connect(self.launchMountainView)

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

        load_whitened_action = open_menu.addAction('&Whitened')
        load_whitened_action.setShortcut('Ctrl+W')
        load_whitened_action.triggered.connect(self.extractWhitened)

        quit_action = file_menu.addAction('&Exit')
        quit_action.setShortcut('Ctrl+Q')
        quit_action.setStatusTip('Exit Program')
        quit_action.triggered.connect(self.disconnectAndQuit)

        # =============== SORT MENU =============== 
        sort_menu = menu_bar.addMenu('&Sort')
        single_session_sort= sort_menu.addAction('&Single')
        single_session_sort.setStatusTip('Sort 1 recording session')
        single_session_sort.triggered.connect(self.sortSingleSession)

        multi_session_sort= sort_menu.addAction('&Multiple')
        multi_session_sort.setStatusTip('Merge and sort multiple recording session')
        multi_session_sort.triggered.connect(self.sortMultiSession)
        # =============== PLOT MENU =============== 
        plot_menu = menu_bar.addMenu('&Plot')

        # =============== PREF MENU =============== 
        preferences_menu = menu_bar.addMenu('Pre&ferences')
        visible_unit_selection = preferences_menu.addAction('&Visible Units')
        visible_unit_selection.setStatusTip('Select visible units')
        visible_unit_selection.triggered.connect(self.getCurrentClusterSelection)

        directories_menu = preferences_menu.addMenu('&Directories')

        output_dir_selection = directories_menu.addAction('&Output directory')
        output_dir_selection.triggered.connect(self.selectOutputDirectory)

        data_dir_selection = directories_menu.addAction('&Data directory')
        data_dir_selection.triggered.connect(self.selectDataDirectory)

        raw_dir_selection = directories_menu.addAction('&Raw directory')
        raw_dir_selection.triggered.connect(self.selectRawDirectory)
        
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
