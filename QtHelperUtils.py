"""
Commandline argument parsing and other helper functions
"""

import os
import sys
import argparse
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget, QFileDialog
from PyQt5.QtWidgets import QCheckBox, QPushButton
from tkinter import Tk, filedialog

USE_QT_FOR_FILEIO = False

def display_warning(info):
    """
    Show a dialog box with the specified message.
    """
    # print('Opening message box ' + info)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText(info)
    msg.setWindowTitle('Warning!')
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()

def display_information(info):
    """
    Show a dialog box with the specified message.
    """
    # print('Opening message box ' + info)
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(info)
    msg.setWindowTitle('Message')
    msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    return msg.exec_()

class CheckBoxWidget(QMessageBox):
  
    """
    Dialog-box containing a number of check-boxes.
    """

    def __init__(self, list_of_elements, message=None):
        """
        Create the dialog-box with a pre-defined list of elements.
        """

        QMessageBox.__init__(self)
        self.setIcon(QMessageBox.Information)
        if message is not None:
            self.setText(message)
        self.setWindowTitle('Message')
        self.checkboxes = list()

        # Set up the layout... All the list elements in a single column
        g_layout = self.layout()

        for el in list_of_elements:
            new_checkbox = QCheckBox(el, self)
            new_checkbox.setChecked(True)
            self.checkboxes.append(new_checkbox)
            g_layout.addWidget(new_checkbox)

        self.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        self.setDefaultButton(QMessageBox.Ok)

    def exec_(self, *args, **kwargs):
        """
        Overloading the exec_() function to get both the messagebox result,
        as well as the selected checkboxes.
        """
        ok = QMessageBox.exec_(self, *args, *kwargs)
        accepted_idxs = list()
        for idx, chk in enumerate(self.checkboxes):
            if chk.isChecked():
                accepted_idxs.append(idx)
        return ok, accepted_idxs

class FileOpenApplication(QWidget):

    """
    Overkill application to just get an open filename
    """

    def __init__(self):
        """TODO: to be defined1. """
        QWidget.__init__(self)

    def getOpenFileName(self, data_dir, message, file_format):
        """
        Get the file path for a user-selected file.
        """
        data_file, _ = QFileDialog.getOpenFileName(self, message,
                data_dir, file_format)
        return data_file

    def getSaveFileName(self, data_dir, message, file_format):
        save_file, _ = QFileDialog.getSaveFileName(self, message, data_dir,\
                file_format)
        return save_file

    def getDirectory(self, data_dir, message):
        return QFileDialog.getExistingDirectory(self, message, data_dir)

# On OSX, getting TK to work seems to be a pain. This is an easier alternative to get the filename
def get_open_file_name(data_dir=None, file_format='All Files (*.*)', message="Choose file"):
    file_dialog = FileOpenApplication()
    if data_dir is None:
        data_dir = os.getcwd()
    file_name = file_dialog.getOpenFileName(str(data_dir), message, file_format)
    file_dialog.close()
    return file_name

def get_save_file_name(data_dir=None, file_format='All Files (*.*)', message="Choose file"):
    file_dialog = FileOpenApplication()
    if data_dir is None:
        data_dir = os.getcwd()
    file_name = file_dialog.getSaveFileName(str(data_dir), message, file_format)
    file_dialog.close()
    return file_name

def get_directory(data_dir=None,message="Choose a directory"):
    file_dialog = FileOpenApplication()
    dir_name = file_dialog.getDirectory(data_dir,message)
    file_dialog.close()
    return dir_name

def parseQtCommandlineArgs(args):
    """
    Parse commandline arguments to get user configuration

    :args: Commandline arguments received from sys.argv
    :returns: Dictionary with aprsed commandline arguments

    """
    parser = argparse.ArgumentParser(description='Spike-Analysis Qt helper.')
    parser.add_argument('--animal', metavar='<animal-name>', help='Animal name')
    parser.add_argument('--date', metavar='YYYYMMDD', help='Experiment date', type=int)
    parser.add_argument('--data-dir', metavar='<[MDA] data-directory>', help='Data directory from which MDA files should be read.')
    parser.add_argument('--raw', metavar='<[npz] raw-data>', help='Raw data to be imported as a numpy archive.')
    parser.add_argument('--bayesian', metavar='<[npz] decoded-data>', help='Decoded data to be imported as a numpy archive.')
    parser.add_argument('--output-dir', metavar='<output-directory>', help='Output directory where sorted spike data should be stored')
    args = parser.parse_args()
    # print(args)
    return args
