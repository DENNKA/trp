import sys
from functools import partial
import traceback
from PyQt5 import QtWidgets

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QStandardItemModel, QTextLayout
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QFrame, QGroupBox, QHBoxLayout, QLabel, QMainWindow, QMdiArea, QMenuBar, QMenu, QAction, QInputDialog, QDialog, QMessageBox, QPushButton, QDialogButtonBox, QSplitter, QTableWidgetItem, QVBoxLayout, QLineEdit, QGridLayout, QCheckBox, QComboBox, QTableWidget, QWidget

from Anime import Anime
import trp

class Window(QMainWindow):
    """Main Window."""
    def __init__(self, trp, cfg, torrent_clients, parent=None):
        """Initializer."""
        super().__init__(parent)
        self.trp = trp
        self.cfg = cfg
        self.torrent_clients = torrent_clients
        self.setWindowTitle("trp - torrent player")
        self.resize(400, 200)
        self.split = QSplitter()
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setFont(QFont("arial", pointSize=9))

        self.split.addWidget(self.table)
        # frame = QGroupBox()
        self.right = QWidget()
        self.info_grid = QGridLayout()
        self.right.setLayout(self.info_grid)
        self.image = QLabel()
        pixmap = QPixmap('img/cover.jpg')
        self.image.setPixmap(pixmap)
        self.info_grid.addWidget(self.image, 1, 1, 2, 2, Qt.AlignTop)
        watch_button = QPushButton("Watch")
        self.info_grid.addWidget(watch_button, 3, 1, Qt.AlignTop)
        delete_button = QPushButton("Delete")
        self.info_grid.addWidget(delete_button, 4, 1, Qt.AlignTop)
        self.split.addWidget(self.right)
        self.split.setStretchFactor(0, 2)
        self.split.setStretchFactor(1, 1)

        # self.split.addWidget(delete_button)
        # self.info_grid.addWidget(frame, 1, 0, 2, 2)
        # self.split.setLayout(self.info_grid)
        self.setCentralWidget(self.split)

        # self.table.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        # self.setCentralWidget(self.table)

        self.checked_columns = cfg['qt']['checked_columns'].split(',')
        self.columns_names =  [key for key, value in Anime().get_dict().items()]
        self.columns_names = self.checked_columns + [x for x in self.columns_names if x not in self.checked_columns]

        self.animes = trp.get_animes()
        self.columns_count = len(self.columns_names)
        self.row_count = len(self.animes)
        self.table.setColumnCount(self.columns_count)
        self.table.setRowCount(self.row_count)
        self.table.setHorizontalHeaderLabels(self.columns_names)
        header = self.table.horizontalHeader()
        header.setDefaultSectionSize(70)
        for i, column in enumerate(self.columns_names):
            if column == "topic":
                # header.setSectionResizeMode(i, QtWidgets.QHeaderView.Fixed)
                header.resizeSection(i, 600)
            try:
                if self.checked_columns.index(column):
                    self.table.showColumn(i)
            except ValueError:
                self.table.hideColumn(i)
        for i in range(self.row_count):
            for j, column_name in enumerate(self.columns_names):
                var = self.animes[i].get_variable(column_name)
                # if type(var) == type(list()) or type(var) == type(dict()):
                    # var = ""
                if column_name == "size":
                    var = self.trp.bytes_to(var, 'g')
                item = QTableWidgetItem(str(var))
                self.table.setItem(i, j, item)

        self.table.cellClicked.connect(self._table_click)

        self._create_actions()
        self._create_menubars()
        self._create_toolbars()
        self._connect_actions()

        # delete_button.clicked.connect(self.action_delete_anime)
        watch_button.clicked.connect(self.watch_anime)
        delete_button.clicked.connect(self.delete_anime)

    def watch_anime(self):
        row = self.table.currentRow()
        anime = self.animes[row]
        self.trp.watch(anime)

    def _table_click(self, row_id):
        self._update_row(self.animes[row_id], row_id)

    def _create_actions(self):
        self.action_new = QAction("&New", self)
        self.action_exit = QAction("&Exit", self)
        self.action_preferences = QAction("&Preferences", self)
        self.action_about = QAction("&About", self)
        self.action_delete_anime = QAction("&Delete anime", self)

    def _update_row(self, anime, row_index = None):
        if row_index == None:
            row_index = self.table.rowCount()
            self.table.insertRow(row_index)

        for j, column_name in enumerate(self.columns_names):
            var = anime.get_variable(column_name)
            if column_name == "size":
                var = self.trp.bytes_to(var, 'g')
            item = QTableWidgetItem(str(var))
            self.table.setItem(row_index, j, item)

    def _update_column(self, column : str, toggle : bool):
        if toggle:
            if column not in self.checked_columns:
                self.checked_columns.append(column)
            self.table.showColumn(self.columns_names.index(column))
        else:
            if column in self.checked_columns:
                self.checked_columns.remove(column)
            self.table.hideColumn(self.columns_names.index(column))

        self.cfg['qt']['checked_columns'] = ','.join(self.checked_columns)
        self.trp.save_cfg()

    def _create_menubars(self):
        menuBar = QMenuBar(self)
        self.setMenuBar(menuBar)

        file_menu = menuBar.addMenu("&File")
        file_menu.addAction(self.action_new)
        file_menu.addAction(self.action_exit)

        edit_menu = menuBar.addMenu("&Edit")
        edit_menu.addAction(self.action_preferences)

        view_menu = menuBar.addMenu("&View")

        help_menu = menuBar.addMenu("&Help")
        help_menu.addAction(self.action_about)

        self.view_anime_menu = view_menu.addMenu("Anime")
        for key, value in Anime().get_dict().items():
            action = QAction(key, self)
            action.setCheckable(True)
            action.setChecked(key in self.checked_columns)
            action.triggered.connect(partial(self._update_column, key))
            self.view_anime_menu.addAction(action)

    def _create_toolbars(self):
        toolbar = self.addToolBar("Toolbar")
        toolbar.addAction(self.action_new)

    def _connect_actions(self):
        self.action_new.triggered.connect(self.add_anime)
        self.action_delete_anime.triggered.connect(self.delete_anime)

    def display_errors(self, exceptions):
        if not len(exceptions): return
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("\n".join([str(x) for x in exceptions]))
        msg.setWindowTitle("Error")
        msg.exec_()

    def _display_error(self, exception):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(str(exception))
        msg.setInformativeText("".join(traceback.TracebackException.from_exception(exception).format()))
        msg.setWindowTitle("Error")
        msg.exec_()

    def add_anime(self):
        add_anime_dialog = AddAnimeDialog(self.trp, self.cfg['trp']['quality'])
        add_anime_dialog.exec_()
        result = add_anime_dialog.get_result()
        if result:
            try:
                anime = self.trp.add_anime(**result)
            except Exception as e:
                self._display_error(e)
                return
            self.trp.update()
            self._update_row(anime)
            self.animes.append(anime)
            if result['instant_play']:
                self.trp.watch(anime)

    def delete_anime(self):
        dialog = QMessageBox()
        remove_button = dialog.addButton("Remove", QMessageBox.YesRole)
        delete_button = dialog.addButton("Delete with all data", QMessageBox.AcceptRole)
        cancel_button = dialog.addButton("Cancel", QMessageBox.NoRole)
        dialog.setDefaultButton(cancel_button)
        dialog.setWindowTitle("Delete anime?")
        dialog.setText("Delete anime?")
        dialog.exec_()
        clicked_button = dialog.clickedButton()
        if clicked_button == remove_button:
            delete = False
        elif clicked_button == delete_button:
            delete = True
        else:
            return

        delete_row = self.table.currentRow()
        self.trp.delete_anime(self.animes[delete_row], delete)
        self.table.removeRow(delete_row)
        del self.animes[delete_row]

class AddAnimeDialog(QDialog):
    def __init__(self, trp, default_quality):
        self.trp = trp
        self.default_quality = default_quality
        super(AddAnimeDialog, self).__init__()

        self.setWindowTitle("New anime")
        self.resize(450, 150)

        self.name_label = QLabel("Name")
        self.quality_label = QLabel("Quality")

        self.name_edit = QLineEdit()
        self.quality_combobox = QComboBox()
        for i, q in enumerate(self.trp.get_quality_list()):
            self.quality_combobox.addItem(str(q))
            if str(q) == default_quality:
                self.quality_combobox.setCurrentIndex(i)
        self.bdremux_checkbox = QCheckBox("BDRemux")

        self.torrent_tracker_label = QLabel("Torrent tracker")
        self.torrent_tracker_combobox = QComboBox()
        for x in self.trp.torrent_trackers.get_all():
            self.torrent_tracker_combobox.addItem(x)

        self.torrent_client_label = QLabel("Torrent client")
        self.torrent_client_combobox = QComboBox()
        for x in self.trp.torrent_clients.get_all():
            self.torrent_client_combobox.addItem(x)

        self.anime_list_label = QLabel("Animelist")
        self.anime_list_combobox = QComboBox()
        self.anime_list_combobox.addItem("")
        for x in self.trp.anime_lists.get_all():
            self.anime_list_combobox.addItem(x)

        self.instant_play_checkbox = QCheckBox("Instant play")

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(self.name_label, 1, 0)
        grid.addWidget(self.name_edit, 1, 1)
        grid.addWidget(self.quality_label, 2, 0)
        grid.addWidget(self.quality_combobox, 2, 1)
        grid.addWidget(self.bdremux_checkbox, 3, 1)
        grid.addWidget(self.torrent_tracker_label, 4, 0)
        grid.addWidget(self.torrent_tracker_combobox, 4, 1)
        grid.addWidget(self.torrent_client_label, 5, 0)
        grid.addWidget(self.torrent_client_combobox, 5, 1)
        grid.addWidget(self.anime_list_label, 6, 0)
        grid.addWidget(self.anime_list_combobox, 6, 1)
        grid.addWidget(self.instant_play_checkbox, 7, 1)

        self.setLayout(grid)

        self.out = ""

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        grid.addWidget(self.buttonBox, 8, 0, 1, 2)

        # self.cancel = QPushButton("Cancel", self)
        # self.ok = QPushButton("Ok", self)

        self.show()

    def accept(self):
        name = self.name_edit.text()
        if len(name) < 1:
            return
        self.out = {"name": name, "quality": self.quality_combobox.currentText(),
                "bdremux_only": self.bdremux_checkbox.checkState(), "torrent_tracker": self.torrent_tracker_combobox.currentText(),
                "torrent_client": self.torrent_client_combobox.currentText(), "anime_list": self.anime_list_combobox.currentText(),
                "instant_play": self.instant_play_checkbox.checkState()}
        self.close()

    def get_result(self):
        return self.out

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec_())
