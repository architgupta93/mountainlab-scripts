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
from PyQt5.QtCore import Qt

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
DEFAULT_ACCESS_TIMESTAMPED_SPIKES = True
DEFAULT_SHOW_GRID_ON_SPIKES = False
FIGURE_BACKGROUND = 'black'
FIGURE_DPI = 1200.0
FIRING_CLIP_SIZE = 32
FIRING_PRE_CLIP = 8
FIRING_POST_CLIP = FIRING_CLIP_SIZE - FIRING_PRE_CLIP
N_ELECTRODE_CHANNELS = 4
SPIKE_MARKER_WIDTH = 0.04
SPIKE_MARKER_SIZE = 0.04
SPIKE_TRANSPARENCY = 0.50
N_CLUSTER_COLORS = 13   # Picking a prime number to get uniform coverage
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

        # The menu item that controls our looking for timestamps in spike mda files.
        self.access_tstamped_selection = None
        self.show_grid_selection = None
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

        self.access_timestamped_firings = DEFAULT_ACCESS_TIMESTAMPED_SPIKES
        self.show_grid_on_spikes = DEFAULT_SHOW_GRID_ON_SPIKES

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
        self.figure  = Figure(figsize=(1024/FIGURE_DPI,1024/FIGURE_DPI), dpi=FIGURE_DPI)
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

    def keyPressEvent(self, e):
        # The following keys are forwarded by the completer to the widget.
        if e.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
            e.ignore()
            # Let the completer do default behavior.
            return

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
        self._ax_ch1v2.set_facecolor(FIGURE_BACKGROUND)
        self._ax_ch1v2.grid(self.show_grid_on_spikes)
        self._ax_ch1v2.set_xlim(self.firing_limits)
        self._ax_ch1v2.set_ylim(self.firing_limits)
        self._ax_ch1v2.set_xticklabels([])
        self._ax_ch1v2.set_yticklabels([])
        if not self.show_grid_on_spikes:
            self._ax_ch1v2.set_xticks([])
            self._ax_ch1v2.set_yticks([])

        self._ax_ch1v3.cla()
        self._ax_ch1v3.set_facecolor(FIGURE_BACKGROUND)
        self._ax_ch1v3.grid(self.show_grid_on_spikes)
        self._ax_ch1v3.set_xlim(self.firing_limits)
        self._ax_ch1v3.set_ylim(self.firing_limits)
        self._ax_ch1v3.set_xticklabels([])
        self._ax_ch1v3.set_yticklabels([])
        if not self.show_grid_on_spikes:
            self._ax_ch1v3.set_xticks([])
            self._ax_ch1v3.set_yticks([])

        self._ax_ch1v4.cla()
        self._ax_ch1v4.set_facecolor(FIGURE_BACKGROUND)
        self._ax_ch1v4.grid(self.show_grid_on_spikes)
        self._ax_ch1v4.set_xlim(self.firing_limits)
        self._ax_ch1v4.set_ylim(self.firing_limits)
        self._ax_ch1v4.set_xticklabels([])
        self._ax_ch1v4.set_yticklabels([])
        if not self.show_grid_on_spikes:
            self._ax_ch1v4.set_xticks([])
            self._ax_ch1v4.set_yticks([])

        self._ax_ch2v3.cla()
        self._ax_ch2v3.set_facecolor(FIGURE_BACKGROUND)
        self._ax_ch2v3.grid(self.show_grid_on_spikes)
        self._ax_ch2v3.set_xlim(self.firing_limits)
        self._ax_ch2v3.set_ylim(self.firing_limits)
        self._ax_ch2v3.set_xticklabels([])
        self._ax_ch2v3.set_yticklabels([])
        if not self.show_grid_on_spikes:
            self._ax_ch2v3.set_xticks([])
            self._ax_ch2v3.set_yticks([])

        self._ax_ch2v4.cla()
        self._ax_ch2v4.set_facecolor(FIGURE_BACKGROUND)
        self._ax_ch2v4.grid(self.show_grid_on_spikes)
        self._ax_ch2v4.set_xlim(self.firing_limits)
        self._ax_ch2v4.set_ylim(self.firing_limits)
        self._ax_ch2v4.set_xticklabels([])
        self._ax_ch2v4.set_yticklabels([])
        if not self.show_grid_on_spikes:
            self._ax_ch2v4.set_xticks([])
            self._ax_ch2v4.set_yticks([])
 
        self._ax_ch3v4.cla()
        self._ax_ch3v4.set_facecolor(FIGURE_BACKGROUND)
        self._ax_ch3v4.grid(self.show_grid_on_spikes)
        self._ax_ch3v4.set_xlim(self.firing_limits)
        self._ax_ch3v4.set_ylim(self.firing_limits)
        self._ax_ch3v4.set_xticklabels([])
        self._ax_ch3v4.set_yticklabels([])
        if not self.show_grid_on_spikes:
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
        self.clearAxes()
        if (not self.show_cluster_widget) or  (self.firing_amplitudes is None):
            return

        taken_colors = list()
        for cl_id in self.currently_selected_clusters:
            spikes_in_cluster = self.clusters[cl_id]
            cluster_color_identifier = int(cl_id) % N_CLUSTER_COLORS
            cluster_color = colormap.hsv(float(cluster_color_identifier)/N_CLUSTER_COLORS)

            # Normalize the cluster color to increase its brightness for the dark background
            # cluster_color = [c_val * 0.25 for c_val in cluster_color]

            if cluster_color_identifier in taken_colors:
                print(MODULE_IDENTIFIER + "Warning: Color repeated while plotting spikes for cluster %s"%cl_id)
            taken_colors.append(cluster_color_identifier)
            # print(spikes_in_cluster)

            # These are the 2D plots
            self._ax_ch1v2.scatter(self.firing_amplitudes[spikes_in_cluster,0], \
                    self.firing_amplitudes[spikes_in_cluster,1], s=SPIKE_MARKER_SIZE, \
                    alpha=SPIKE_TRANSPARENCY, color=cluster_color, marker='.', \
                    lw=SPIKE_MARKER_WIDTH)
            self._ax_ch1v3.scatter(self.firing_amplitudes[spikes_in_cluster,0], \
                    self.firing_amplitudes[spikes_in_cluster,2], s=SPIKE_MARKER_SIZE, \
                    alpha=SPIKE_TRANSPARENCY, color=cluster_color, marker='.', \
                    lw=SPIKE_MARKER_WIDTH)
            self._ax_ch1v4.scatter(self.firing_amplitudes[spikes_in_cluster,0], \
                    self.firing_amplitudes[spikes_in_cluster,3], s=SPIKE_MARKER_SIZE, \
                    alpha=SPIKE_TRANSPARENCY, color=cluster_color, marker='.', \
                    lw=SPIKE_MARKER_WIDTH)
            self._ax_ch2v3.scatter(self.firing_amplitudes[spikes_in_cluster,1], \
                    self.firing_amplitudes[spikes_in_cluster,2], s=SPIKE_MARKER_SIZE, \
                    alpha=SPIKE_TRANSPARENCY, color=cluster_color, marker='.', \
                    lw=SPIKE_MARKER_WIDTH)
            self._ax_ch2v4.scatter(self.firing_amplitudes[spikes_in_cluster,1], \
                    self.firing_amplitudes[spikes_in_cluster,3], s=SPIKE_MARKER_SIZE, \
                    alpha=SPIKE_TRANSPARENCY, color=cluster_color, marker='.', \
                    lw=SPIKE_MARKER_WIDTH)
            self._ax_ch3v4.scatter(self.firing_amplitudes[spikes_in_cluster,2], \
                    self.firing_amplitudes[spikes_in_cluster,3], s=SPIKE_MARKER_SIZE, \
                    alpha=SPIKE_TRANSPARENCY, color=cluster_color, marker='.', \
                    lw=SPIKE_MARKER_WIDTH)
        self.canvas.draw()

    def fetchTetrodeData(self, _):
        """
        Fetch spikes and clips/whitened data for the current tetrode and display it.
        """
        tetrode_id = self.tetrode_selection.currentText()
        if self.output_dir is None:
            self.output_dir = QtHelperUtils.get_directory(message="Choose firings data directory.")
        tetrode_dir = os.path.join(self.output_dir, 'nt' + tetrode_id)
        if self.access_timestamped_firingS:
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

        # spike_indices = np.searchsorted(self.timestamp_data, self.firing_data[1])
        if self.access_timestamped_firings:
            spike_indices = np.searchsorted(self.timestamp_data, self.firing_data[1])
            print(self.timestamp_data)
            print(spike_indices)
            print(MODULE_IDENTIFIER + "Timestamped clips extracted")
        else:
            spike_indices = np.array(self.firing_data[1], dtype='int')
            print(MODULE_IDENTIFIER + "Indexed clips extracted")
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

        print(self.firing_amplitudes.shape)
        self.firing_limits = (max(-500,np.min(self.firing_amplitudes)), \
                min(3000, np.mean(self.firing_amplitudes) + 5.0 * np.std(self.firing_amplitudes)))
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

    def saveScreenshot(self):
        """
        Save the current screen content as an image
        """
        # Create a filename
        # The custom name feature is already present in the navigation toolbar. This function can be used to save data programatically
        # save_file_name = QtHelperUtils.get_save_file_name(data_dir=self.output_dir, file_format='Image File (*.jpg)', message="Choose a screenshot name")
        save_file_name = time.strftime("T" + str(self.tetrode_selection.currentText()) + "U" + str(self.unit_selection.currentText()) + "_%Y%m%d_%H%M%S.png") 
        save_success = False
        try:
            self.figure.savefig(save_file_name)
            save_success = True
        except Exception as err:
            print(MODULE_IDENTIFIER + "Unable to save current display.")
            print(err)

        if save_success:
            self.statusBar().showMessage("Screenshot saved to %s"%save_file_name)

    def showExampleWaveforms(self):
        """
        Show example waveforms from the current spike selection.
        """
        if self.firing_clips is None:
            QtHelperUtils.display_warning("Clip data not loaded to extract example waveforms from.")
            return

        # TODO: Account for the spieks that are being shown at the moment.
        # For now, we are just showing a random set of spikes to make sure that things look sane
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

        user_choices = QtHelperUtils.CheckBoxWidget(processing_args, message="Select clusters to view", \
                default_choices=default_selection_choice).exec_()
        if user_choices[0] == QDialog.Accepted:
            if self.currently_selected_clusters is not None:
                self.currently_selected_clusters.clear()
            else:
                self.currently_selected_clusters = list()

            print(MODULE_IDENTIFIER + "Selected clusters are...")
            print(self.cluster_names)
            for accepted_idx in user_choices[1]:
                self.currently_selected_clusters.append(self.cluster_names[accepted_idx])

            # Sort the cluster identities so that the plot order is consistent.
            self.currently_selected_clusters.sort()

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
        print(MODULE_IDENTIFIER + "Firing data loaded from %s"%firings_filename)

    def toggleTimestampedSikes(self, state):
        self.access_tstamped_selection.setChecked(state)
        self.access_timestamped_firings = state

    def toggleShowGrids(self, state):
        self.show_grid_selection.setChecked(state)
        self.show_grid_on_spikes = state
        self.refresh(False)

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

    def clearData(self):
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

        # Clear all the data stored presently
        clear_action = file_menu.addAction('&Clear')
        clear_action.setStatusTip('Clear/Reset all the data saved in the application')
        clear_action.triggered.connect(self.clearData)

        # =============== SAVE MENU =============== 
        save_menu = file_menu.addMenu('&Save')
        save_screenshot_menu = save_menu.addAction('&Screenshot')
        save_screenshot_menu.setStatusTip('Save current view to computer')
        save_screenshot_menu.triggered.connect(self.saveScreenshot)

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
        example_waveforms_menu = plot_menu.addAction('&Example Waveforms')
        example_waveforms_menu.setStatusTip('Show example waveforms from the current spike selection.')
        example_waveforms_menu.triggered.connect(self.showExampleWaveforms)

        # =============== PREF MENU =============== 
        preferences_menu = menu_bar.addMenu('Pre&ferences')
        visible_unit_selection = preferences_menu.addAction('&Visible Units')
        visible_unit_selection.setStatusTip('Select visible units')
        visible_unit_selection.triggered.connect(self.getCurrentClusterSelection)

        self.access_tstamped_selection = QAction('&Timestamped Spike Data', self, checkable=True)
        self.access_tstamped_selection.setStatusTip('Assume that spike MDAs have timestamps instead of time indices.')
        self.access_tstamped_selection.setChecked(DEFAULT_ACCESS_TIMESTAMPED_SPIKES)
        self.access_tstamped_selection.triggered.connect(self.toggleTimestampedSikes)

        self.show_grid_selection = QAction('Show &grid', self, checkable=True)
        self.show_grid_selection.setStatusTip('Show grid on the spike amplitude plots')
        self.show_grid_selection.setChecked(DEFAULT_SHOW_GRID_ON_SPIKES)
        self.show_grid_selection.triggered.connect(self.toggleShowGrids)

        preferences_menu.addAction(self.access_tstamped_selection)
        preferences_menu.addAction(self.show_grid_selection)

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
