import enum
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Tuple

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSettings,
    QSize,
    QStandardPaths,
    QTimer,
    QUrl,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QContextMenuEvent,
    QCursor,
    QFocusEvent,
    QFont,
    QIcon,
    QKeyEvent,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QShortcut,
    QKeySequence,
)
from PyQt6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollBar,
    QStackedWidget,
    QStyleOptionSlider,
    QTableWidget,
    QTableWidgetItem,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# ==========================================
# Constants & Styling Configuration
# ==========================================

WINDOW_TITLE = "Zenith Browser"
DEFAULT_WINDOW_SIZE = QSize(1200, 750)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOME_PAGE_FILE = os.path.join(BASE_DIR, "pages", "home.html")
HELP_PAGE_FILE = os.path.join(BASE_DIR, "pages", "help.html")

DEFAULT_ENGINE = "duckduckgo"

SEARCH_ENGINES: Dict[str, str] = {
    "google": "https://www.google.com/search?q={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
    "brave": "https://search.brave.com/search?q={}",
    "bing": "https://www.bing.com/search?q={}",
    "kagi": "https://kagi.com/search?q={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
    "github": "https://github.com/search?q={}",
    "reddit": "https://www.reddit.com/search/?q={}",
}

ENGINE_PREFIXES: Dict[str, str] = {
    "g": "google",
    "d": "duckduckgo",
    "b": "brave",
    "k": "kagi",
    "gh": "github",
    "yt": "youtube",
    "r": "reddit",
}

OVERLAY_BACKDROP_COLOR = QColor(0, 0, 0, 160)
CARD_BG_COLOR = QColor(24, 24, 28, 235)
CARD_BORDER_COLOR = QColor(255, 255, 255, 35)
CARD_BORDER_FOCUS_COLOR = QColor(99, 102, 241, 200)
TEXT_COLOR = QColor(240, 240, 245)
PLACEHOLDER_COLOR = QColor(140, 140, 155)
ICON_COLOR = QColor(160, 160, 175)

CORNER_RADIUS = 18
ANIMATION_DURATION_MS = 180

# Injectable Modern Overlay Scrollbar CSS for WebEngine
MODERN_SCROLLBAR_CSS = """
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: transparent;
}
::-webkit-scrollbar-thumb {
    background: rgba(160, 160, 175, 0.25);
    border-radius: 4px;
    transition: background 0.3s ease;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(99, 102, 241, 0.8);
}
::-webkit-scrollbar-corner {
    background: transparent;
}
"""


# ==========================================
# Persistent Profiles & Data Storage Architecture
# ==========================================

@dataclass
class BrowserProfile:
    name: str
    avatar: str = "🟢"
    path: str = ""
    settings: Dict = field(default_factory=dict)

    def get_cookies_path(self) -> str:
        return os.path.join(self.path, "Cookies")

    def get_cache_path(self) -> str:
        return os.path.join(self.path, "Cache")

    def get_storage_path(self) -> str:
        return os.path.join(self.path, "Storage")

    def get_downloads_path(self) -> str:
        return os.path.join(self.path, "Downloads")

    def get_file(self, filename: str) -> str:
        return os.path.join(self.path, filename)


class BrowserDataManager:
    """Manages profile JSON files (Bookmarks, History, Downloads, Settings, Session)."""

    def __init__(self, profile: BrowserProfile) -> None:
        self.profile = profile

    def _read_json(self, filename: str, default: any) -> any:
        filepath = self.profile.get_file(filename)
        if not os.path.exists(filepath):
            return default
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _write_json(self, filename: str, data: any) -> None:
        filepath = self.profile.get_file(filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving {filename}: {e}")

    # Bookmarks
    def load_bookmarks(self) -> List[Dict]:
        return self._read_json("Bookmarks.json", [])

    def save_bookmarks(self, bookmarks: List[Dict]) -> None:
        self._write_json("Bookmarks.json", bookmarks)

    # History
    def load_history(self) -> List[Dict]:
        return self._read_json("History.json", [])

    def add_history_entry(self, title: str, url: str) -> None:
        if not url or url.startswith("about:") or url.startswith("chrome:"):
            return
        history = self.load_history()
        now = datetime.now().isoformat()
        found = False
        for item in history:
            if item.get("url") == url:
                item["visit_count"] = item.get("visit_count", 0) + 1
                item["last_visited"] = now
                item["title"] = title or item.get("title", url)
                found = True
                break
        if not found:
            history.append({
                "title": title or url,
                "url": url,
                "visit_count": 1,
                "last_visited": now
            })
        self._write_json("History.json", history)

    # Downloads
    def load_downloads(self) -> List[Dict]:
        return self._read_json("Downloads.json", [])

    def add_download_entry(self, filename: str, path: str, size: int) -> None:
        downloads = self.load_downloads()
        downloads.append({
            "filename": filename,
            "path": path,
            "size": size,
            "date": datetime.now().isoformat()
        })
        self._write_json("Downloads.json", downloads)

    # Settings
    def load_settings(self) -> Dict:
        defaults = {
            "theme": "dark",
            "accent_color": "#6366F1",
            "homepage": HOME_PAGE_FILE,
            "search_engine": DEFAULT_ENGINE,
            "zoom_level": 1.0,
            "ad_blocker_mode": "Balanced",
            "restore_session": True,
            "enabled_extensions": ["shorts_blocker", "inspect_element", "quick_commands"]
        }
        loaded = self._read_json("Settings.json", {})
        defaults.update(loaded)
        return defaults

    def save_settings(self, settings: Dict) -> None:
        self._write_json("Settings.json", settings)


class ProfileManager:
    """Production-quality profile management system for unlimited isolated profiles."""

    def __init__(self, base_dir: str = "profiles") -> None:
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)
        self.active_profile: Optional[BrowserProfile] = None
        self.web_engine_profile: Optional[QWebEngineProfile] = None
        self.data_manager: Optional[BrowserDataManager] = None

        self._ensure_default_profile()
        self.load_profile(self.get_last_active_profile_name())

    def get_all_profiles(self) -> List[str]:
        profiles = []
        if os.path.exists(self.base_dir):
            for entry in os.listdir(self.base_dir):
                full_path = os.path.join(self.base_dir, entry)
                if os.path.isdir(full_path):
                    profiles.append(entry)
        return profiles if profiles else ["Default"]

    def _ensure_default_profile(self) -> None:
        default_dir = os.path.join(self.base_dir, "Default")
        if not os.path.exists(default_dir):
            self.create_profile("Default", "🔵")

    def get_last_active_profile_name(self) -> str:
        global_settings = QSettings("ZenithBrowser", "Profiles")
        name = global_settings.value("last_profile", "Default", type=str)
        if name not in self.get_all_profiles():
            name = "Default"
        return name

    def create_profile(self, name: str, avatar: str = "🟢") -> BrowserProfile:
        name = name.strip() or "Profile"
        path = os.path.join(self.base_dir, name)
        os.makedirs(path, exist_ok=True)
        for folder in ["Cookies", "Cache", "Storage", "Downloads"]:
            os.makedirs(os.path.join(path, folder), exist_ok=True)

        profile_meta = {"name": name, "avatar": avatar, "created": datetime.now().isoformat()}
        meta_file = os.path.join(path, "Profile.json")
        if not os.path.exists(meta_file):
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(profile_meta, f, indent=4)

        return BrowserProfile(name=name, avatar=avatar, path=path)

    def load_profile(self, name: str) -> BrowserProfile:
        path = os.path.join(self.base_dir, name)
        if not os.path.exists(path):
            return self.create_profile(name)

        meta_file = os.path.join(path, "Profile.json")
        avatar = "🟢"
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    avatar = meta.get("avatar", "🟢")
            except Exception:
                pass

        profile = BrowserProfile(name=name, avatar=avatar, path=path)
        self.active_profile = profile
        self.data_manager = BrowserDataManager(profile)

        # Save active selection
        global_settings = QSettings("ZenithBrowser", "Profiles")
        global_settings.setValue("last_profile", name)

        # Configure isolated QWebEngineProfile
        self._setup_web_engine_profile(profile)
        return profile

    def _setup_web_engine_profile(self, profile: BrowserProfile) -> None:
        storage_name = f"Zenith_{profile.name}"
        self.web_engine_profile = QWebEngineProfile(storage_name, None)
        self.web_engine_profile.setPersistentStoragePath(profile.get_storage_path())
        self.web_engine_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        self.web_engine_profile.setCachePath(profile.get_cache_path())
        self.web_engine_profile.setDownloadPath(profile.get_downloads_path())

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        if old_name == new_name or not new_name.strip():
            return False
        old_path = os.path.join(self.base_dir, old_name)
        new_path = os.path.join(self.base_dir, new_name)
        if os.path.exists(new_path):
            return False
        try:
            os.rename(old_path, new_path)
            if self.active_profile and self.active_profile.name == old_name:
                self.load_profile(new_name)
            return True
        except Exception:
            return False

    def delete_profile(self, name: str) -> bool:
        if name == "Default":
            return False
        path = os.path.join(self.base_dir, name)
        if os.path.exists(path):
            import shutil
            try:
                shutil.rmtree(path)
                if self.active_profile and self.active_profile.name == name:
                    self.load_profile("Default")
                return True
            except Exception:
                return False
        return False


class SessionManager:
    """Manages saving and restoring tab sessions, geometries, and state."""

    def __init__(self, profile_manager: ProfileManager) -> None:
        self.profile_manager = profile_manager

    def save_session(self, main_window: "MainWindow") -> None:
        if not self.profile_manager.data_manager:
            return
        
        tabs_data = []
        for i in range(main_window.tab_widget.count()):
            widget = main_window.tab_widget.widget(i)
            if isinstance(widget, CustomWebEngineView):
                tabs_data.append({
                    "url": widget.url().toString(),
                    "title": widget.title(),
                    "history": widget.export_history_data()
                })

        session = {
            "active_tab": main_window.tab_widget.currentIndex(),
            "tabs": tabs_data,
            "window_geometry": main_window.saveGeometry().toHex().data().decode("utf-8"),
            "window_state": main_window.saveState().toHex().data().decode("utf-8"),
            "is_maximized": main_window.isMaximized()
        }
        self.profile_manager.data_manager._write_json("Session.json", session)

    def load_session(self) -> Optional[Dict]:
        if not self.profile_manager.data_manager:
            return None
        return self.profile_manager.data_manager._read_json("Session.json", None)


# ==========================================
# Profile Selector Overlay / Dialog
# ==========================================

class ProfileSelectorDialog(QDialog):
    """Modern popup matching Zenith's UI for profile management."""

    def __init__(self, profile_manager: ProfileManager, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.selected_profile_name: Optional[str] = None
        self.action_taken: str = ""  # "switch", "reload"

        self.setWindowTitle("Profile Switcher")
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog {
                background-color: #18181B;
                color: #F4F4F5;
            }
            QLabel {
                color: #F4F4F5;
            }
            QListWidget {
                background: #1C1C20;
                border: 1px solid #27272A;
                border-radius: 8px;
                color: #F4F4F5;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #27272A;
            }
            QListWidget::item:selected {
                background: #6366F1;
                color: #FFFFFF;
            }
            QPushButton {
                background: #27272A;
                color: #F4F4F5;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3F3F46;
            }
            QPushButton#PrimaryBtn {
                background: #6366F1;
                border: 1px solid #818CF8;
            }
            QPushButton#PrimaryBtn:hover {
                background: #4F46E5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        curr = profile_manager.active_profile
        curr_name = curr.name if curr else "Default"
        curr_avatar = curr.avatar if curr else "🟢"

        header = QLabel(f"{curr_avatar}  Current Profile: <b>{curr_name}</b>", self)
        header.setFont(QFont("Inter", 12))
        layout.addWidget(header)

        layout.addWidget(QLabel("Select or Manage Profile:", self))

        self.list_widget = QListWidget(self)
        self._populate_list()
        layout.addWidget(self.list_widget)

        btn_grid1 = QHBoxLayout()
        btn_switch = QPushButton("Switch Profile", self)
        btn_switch.setObjectName("PrimaryBtn")
        btn_switch.clicked.connect(self._on_switch)

        btn_create = QPushButton("Create Profile", self)
        btn_create.clicked.connect(self._on_create)

        btn_grid1.addWidget(btn_switch)
        btn_grid1.addWidget(btn_create)
        layout.addLayout(btn_grid1)

        btn_grid2 = QHBoxLayout()
        btn_rename = QPushButton("Rename Profile", self)
        btn_rename.clicked.connect(self._on_rename)

        btn_delete = QPushButton("Delete Profile", self)
        btn_delete.clicked.connect(self._on_delete)

        btn_folder = QPushButton("Open Directory", self)
        btn_folder.clicked.connect(self._on_open_folder)

        btn_grid2.addWidget(btn_rename)
        btn_grid2.addWidget(btn_delete)
        btn_grid2.addWidget(btn_folder)
        layout.addLayout(btn_grid2)

    def _populate_list(self) -> None:
        self.list_widget.clear()
        profiles = self.profile_manager.get_all_profiles()
        curr = self.profile_manager.active_profile.name if self.profile_manager.active_profile else ""
        for name in profiles:
            item = QListWidgetItem(f"👤  {name}" + (" (Active)" if name == curr else ""))
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list_widget.addItem(item)
            if name == curr:
                self.list_widget.setCurrentItem(item)

    def _get_selected_name(self) -> Optional[str]:
        item = self.list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_switch(self) -> None:
        name = self._get_selected_name()
        if name:
            self.selected_profile_name = name
            self.action_taken = "switch"
            self.accept()

    def _on_create(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Create Profile", "Enter new profile name:")
        if ok and name.strip():
            self.profile_manager.create_profile(name.strip())
            self._populate_list()

    def _on_rename(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        target = self._get_selected_name()
        if not target:
            return
        new_name, ok = QInputDialog.getText(self, "Rename Profile", f"Rename profile '{target}' to:")
        if ok and new_name.strip():
            if self.profile_manager.rename_profile(target, new_name.strip()):
                self._populate_list()
                self.action_taken = "reload"

    def _on_delete(self) -> None:
        target = self._get_selected_name()
        if not target or target == "Default":
            QMessageBox.warning(self, "Error", "Cannot delete Default profile.")
            return
        res = QMessageBox.question(self, "Confirm Delete", f"Delete profile '{target}' and all its isolated data?")
        if res == QMessageBox.StandardButton.Yes:
            self.profile_manager.delete_profile(target)
            self._populate_list()
            self.action_taken = "reload"

    def _on_open_folder(self) -> None:
        target = self._get_selected_name()
        if target:
            path = os.path.join(self.profile_manager.base_dir, target)
            os.makedirs(path, exist_ok=True)
            import subprocess
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])


# ==========================================
# 3. Modern Qt Overlay Scrollbar Component
# ==========================================

class ModernScrollBar(QScrollBar):
    """Modern auto-hiding overlay scrollbar for Qt widgets."""

    def __init__(self, orientation: Qt.Orientation, parent: Optional[QWidget] = None) -> None:
        super().__init__(orientation, parent)
        self.setMouseTracking(True)
        self._opacity = 0.0
        self._hovered = False

        self.fade_anim = QPropertyAnimation(self, b"opacity")
        self.fade_anim.setDuration(250)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._start_fade_out)

        self.valueChanged.connect(self._on_user_activity)
        self.rangeChanged.connect(self._on_user_activity)

        self.setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(160, 160, 175, 0.3);
                min-height: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6366F1;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(160, 160, 175, 0.3);
                min-width: 24px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #6366F1;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
        """)

    @pyqtProperty(float)
    def opacity(self) -> float:
        return self._opacity

    @opacity.setter
    def opacity(self, val: float) -> None:
        self._opacity = val
        self.update()

    def _on_user_activity(self) -> None:
        self._show_scrollbar()
        self.hide_timer.start(1500)

    def _show_scrollbar(self) -> None:
        if self._opacity < 1.0:
            self.fade_anim.stop()
            self.fade_anim.setStartValue(self._opacity)
            self.fade_anim.setEndValue(1.0)
            self.fade_anim.start()

    def _start_fade_out(self) -> None:
        if not self._hovered:
            self.fade_anim.stop()
            self.fade_anim.setStartValue(self._opacity)
            self.fade_anim.setEndValue(0.0)
            self.fade_anim.start()

    def enterEvent(self, event: QEnterEvent) -> None:
        self._hovered = True
        self._show_scrollbar()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovered = False
        self.hide_timer.start(1000)
        super().leaveEvent(event)

    def paintEvent(self, event: QEvent) -> None:
        if self._opacity <= 0.0:
            return
        painter = QPainter(self)
        painter.setOpacity(self._opacity)
        super().paintEvent(event)


# ==========================================
# 1. Advanced EasyList/uBlock Ad Blocker Engine
# ==========================================

class AdBlockMode(enum.Enum):
    STRICT = "Strict"
    BALANCED = "Balanced"
    DISABLED = "Disabled"


@dataclass
class FilterListInfo:
    name: str
    enabled: bool = True
    rules_count: int = 0


class AdBlocker(QWebEngineUrlRequestInterceptor):
    """Production-grade request interceptor supporting domain matching & EasyList rule parsing."""

    stats_updated = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.mode = AdBlockMode.BALANCED
        self.session_ads_blocked = 0
        self.session_trackers_blocked = 0
        self.page_stats: Dict[str, Dict[str, int]] = {}

        self.filter_lists: Dict[str, FilterListInfo] = {
            "EasyList": FilterListInfo("EasyList", True, 0),
            "EasyPrivacy": FilterListInfo("EasyPrivacy", True, 0),
            "Zenith Shield": FilterListInfo("Zenith Shield", True, 0),
        }

        self.blocked_domains_ad: Set[str] = set()
        self.blocked_domains_tracker: Set[str] = set()
        self.regex_rules_ad: List[re.Pattern] = []
        self.regex_rules_tracker: List[re.Pattern] = []

        self._load_default_filter_rules()

    def _load_default_filter_rules(self) -> None:
        default_ads = [
            "doubleclick.net", "googlesyndication.com", "googleadservices.com",
            "adservice.google.com", "amazon-adsystem.com", "ads.yahoo.com",
            "taboola.com", "outbrain.com", "adnxs.com", "rubiconproject.com",
            "criteo.com", "openx.net", "pubmatic.com", "adsystem.com",
            "adservice.com", "adform.net", "media.net", "serving-sys.com",
            "zedo.com", "popads.net", "propellerads.com", "adroll.com"
        ]

        default_trackers = [
            "google-analytics.com", "scorecardresearch.com", "pixel.facebook.com",
            "analytics.facebook.com", "connect.facebook.net/en_US/fbevents.js",
            "bing.com/action", "hotjar.com", "crazyegg.com", "mixpanel.com",
            "clarity.ms", "segment.io", "segment.com", "amplitude.com",
            "quantserve.com", "chartbeat.com", "matomo.org", "piwik.org",
            "mouseflow.com", "fullstory.com", "yandex.ru/metrika"
        ]

        for ad in default_ads:
            self.blocked_domains_ad.add(ad)
        for tr in default_trackers:
            self.blocked_domains_tracker.add(tr)

        self.filter_lists["Zenith Shield"].rules_count = len(default_ads) + len(default_trackers)
        self.filter_lists["EasyList"].rules_count = len(default_ads) * 3
        self.filter_lists["EasyPrivacy"].rules_count = len(default_trackers) * 3

    def import_filter_list(self, name: str, content: str) -> None:
        lines = content.splitlines()
        count = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith("!") or line.startswith("##"):
                continue
            if line.startswith("||"):
                domain = line[2:].rstrip("^").split("^")[0].lower()
                if domain:
                    self.blocked_domains_ad.add(domain)
                    count += 1
            elif line.startswith("|http"):
                clean = line.strip("|")
                try:
                    pattern = re.compile(re.escape(clean).replace(r"\*", ".*"))
                    self.regex_rules_ad.append(pattern)
                    count += 1
                except re.error:
                    pass

        self.filter_lists[name] = FilterListInfo(name=name, enabled=True, rules_count=count)
        self.stats_updated.emit()

    def set_mode(self, mode: AdBlockMode) -> None:
        self.mode = mode
        self.stats_updated.emit()

    def set_filter_enabled(self, name: str, enabled: bool) -> None:
        if name in self.filter_lists:
            self.filter_lists[name].enabled = enabled
            self.stats_updated.emit()

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        if self.mode == AdBlockMode.DISABLED:
            return

        url_str = info.requestUrl().toString().lower()
        first_party = info.firstPartyUrl().toString()

        is_ad, is_tracker = self._check_should_block(url_str)

        if is_ad or is_tracker:
            info.block(True)
            if is_ad:
                self.session_ads_blocked += 1
            if is_tracker:
                self.session_trackers_blocked += 1

            if first_party:
                if first_party not in self.page_stats:
                    self.page_stats[first_party] = {"ads": 0, "trackers": 0}
                if is_ad:
                    self.page_stats[first_party]["ads"] += 1
                if is_tracker:
                    self.page_stats[first_party]["trackers"] += 1

            self.stats_updated.emit()

    def _check_should_block(self, url_str: str) -> Tuple[bool, bool]:
        is_ad = any(domain in url_str for domain in self.blocked_domains_ad)
        is_tracker = any(domain in url_str for domain in self.blocked_domains_tracker)

        if not is_ad:
            is_ad = any(rx.search(url_str) for rx in self.regex_rules_ad)

        if self.mode == AdBlockMode.STRICT:
            if not is_ad:
                is_ad = any(kw in url_str for kw in ["/ads/", "/adserv", "banner", "popunder", "telemetry"])
            if not is_tracker:
                is_tracker = any(kw in url_str for kw in ["tracking", "beacon", "log_event", "metrics"])

        return is_ad, is_tracker

    def get_page_stats(self, url_str: str) -> Tuple[int, int]:
        stats = self.page_stats.get(url_str, {"ads": 0, "trackers": 0})
        return stats["ads"], stats["trackers"]

    def reset_stats(self) -> None:
        self.session_ads_blocked = 0
        self.session_trackers_blocked = 0
        self.page_stats.clear()
        self.stats_updated.emit()


# ==========================================
# Dynamic Custom WebEngineView with Mouse Link Intercept
# ==========================================

class CustomWebEngineView(QWebEngineView):
    """Custom view maintaining independent navigation history state & mouse gestures."""

    open_in_background_requested = pyqtSignal(QUrl)

    def __init__(self, profile: QWebEngineProfile, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        page = QWebEnginePage(profile, self)
        self.setPage(page)
        self.custom_history_stack: List[str] = []

    def createWindow(self, type_: QWebEnginePage.WebWindowType) -> Optional[QWebEngineView]:
        main_win = self.window()
        if isinstance(main_win, MainWindow):
            idx = main_win.add_tab()
            return main_win.tab_widget.widget(idx)
        return super().createWindow(type_)

    def export_history_data(self) -> List[str]:
        return self.custom_history_stack.copy()

    def import_history_data(self, history: List[str]) -> None:
        self.custom_history_stack = history.copy()


# ==========================================
# 2. Ad Block Glass Popup Widget
# ==========================================

class AdBlockPopup(QWidget):
    """Floating popup displaying shield status, filter toggles, and live counters."""

    mode_changed = pyqtSignal(AdBlockMode)
    reset_stats_requested = pyqtSignal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()

        self._opacity = 0.0
        self._scale = 0.95
        self.current_mode = AdBlockMode.BALANCED

        self._init_ui()
        self._init_animations()
        parent.installEventFilter(self)

    def _init_ui(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame(self)
        self.card.setObjectName("AdBlockCard")
        self.card.setFixedWidth(380)
        self.card.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.shield_icon = QLabel(self.card)
        self.shield_icon.setFixedSize(26, 26)
        self._draw_shield_pixmap(QColor("#6366F1"))

        title = QLabel("Zenith Shield & Ad Blocker", self.card)
        title.setFont(QFont("Inter", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_COLOR.name()};")

        header_layout.addWidget(self.shield_icon)
        header_layout.addWidget(title)
        header_layout.addStretch()

        card_layout.addLayout(header_layout)

        mode_label = QLabel("Protection Mode", self.card)
        mode_label.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        mode_label.setStyleSheet("color: #A1A1AA;")
        card_layout.addWidget(mode_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_strict = QPushButton("Strict", self.card)
        self.btn_strict.setToolTip("Aggressively block all ad networks, trackers, popups & scripts.")

        self.btn_balanced = QPushButton("Balanced", self.card)
        self.btn_balanced.setToolTip("Default. Blocks ads and trackers while maximizing site performance.")

        self.btn_disabled = QPushButton("Disabled", self.card)
        self.btn_disabled.setToolTip("Disable filtering entirely for this session.")

        for btn, mode in [
            (self.btn_strict, AdBlockMode.STRICT),
            (self.btn_balanced, AdBlockMode.BALANCED),
            (self.btn_disabled, AdBlockMode.DISABLED),
        ]:
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, m=mode: self.mode_changed.emit(m))
            btn_layout.addWidget(btn)

        card_layout.addLayout(btn_layout)

        stats_label = QLabel("Live Block Counter", self.card)
        stats_label.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        stats_label.setStyleSheet("color: #A1A1AA; margin-top: 4px;")
        card_layout.addWidget(stats_label)

        stats_grid = QVBoxLayout()
        stats_grid.setSpacing(6)

        self.lbl_page_ads = self._create_stat_row("Ads blocked this page:", "0", stats_grid)
        self.lbl_page_trackers = self._create_stat_row("Trackers blocked this page:", "0", stats_grid)
        self.lbl_session_ads = self._create_stat_row("Ads blocked this session:", "0", stats_grid)
        self.lbl_session_trackers = self._create_stat_row("Trackers blocked this session:", "0", stats_grid)

        card_layout.addLayout(stats_grid)

        self.btn_reset = QPushButton("Reset Statistics", self.card)
        self.btn_reset.setFixedHeight(30)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background: #27272A;
                color: #A1A1AA;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #3F3F46;
                color: #FFFFFF;
            }
        """)
        self.btn_reset.clicked.connect(self.reset_stats_requested.emit)
        card_layout.addWidget(self.btn_reset)

        main_layout.addWidget(self.card)
        self._update_button_styles()

    def _draw_shield_pixmap(self, color: QColor) -> None:
        pixmap = QPixmap(26, 26)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.moveTo(13, 2)
        path.cubicTo(13, 2, 4, 3, 4, 11)
        path.cubicTo(4, 18, 13, 24, 13, 24)
        path.cubicTo(13, 24, 22, 18, 22, 11)
        path.cubicTo(22, 3, 13, 2, 13, 2)

        painter.setPen(QPen(color, 2))
        painter.drawPath(path)
        painter.end()
        self.shield_icon.setPixmap(pixmap)

    def _create_stat_row(self, label_text: str, default_val: str, layout: QVBoxLayout) -> QLabel:
        row = QHBoxLayout()
        lbl = QLabel(label_text, self.card)
        lbl.setStyleSheet("color: #A1A1AA; font-size: 11px;")
        val = QLabel(default_val, self.card)
        val.setStyleSheet("color: #F4F4F5; font-size: 11px; font-weight: bold;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)
        return val

    def _init_animations(self) -> None:
        self.fade_anim = QPropertyAnimation(self, b"overlayOpacity")
        self.fade_anim.setDuration(ANIMATION_DURATION_MS)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.scale_anim = QPropertyAnimation(self, b"overlayScale")
        self.scale_anim.setDuration(ANIMATION_DURATION_MS)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.fade_anim)
        self.anim_group.addAnimation(self.scale_anim)

    @pyqtProperty(float)
    def overlayOpacity(self) -> float:
        return self._opacity

    @overlayOpacity.setter
    def overlayOpacity(self, val: float) -> None:
        self._opacity = val
        self.update()

    @pyqtProperty(float)
    def overlayScale(self) -> float:
        return self._scale

    @overlayScale.setter
    def overlayScale(self, val: float) -> None:
        self._scale = val
        self.card.setGeometry(self._calculate_card_rect())
        self.update()

    def _calculate_card_rect(self) -> QRect:
        w, h = 380, self.card.sizeHint().height()
        sw = int(w * self._scale)
        sh = int(h * self._scale)
        x = (self.width() - sw) // 2
        y = (self.height() - sh) // 2
        return QRect(x, y, sw, sh)

    def open_popup(self) -> None:
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())

        self.show()
        self.raise_()
        self.setFocus()

        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)

        self.scale_anim.setStartValue(0.95)
        self.scale_anim.setEndValue(1.0)

        self.anim_group.stop()
        self.anim_group.start()

    def close_popup(self) -> None:
        self.fade_anim.setStartValue(self._opacity)
        self.fade_anim.setEndValue(0.0)

        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(0.95)

        self.anim_group.stop()
        try:
            self.anim_group.finished.disconnect()
        except TypeError:
            pass
        self.anim_group.finished.connect(self._finish_close)
        self.anim_group.start()

    def _finish_close(self) -> None:
        self.hide()
        try:
            self.anim_group.finished.disconnect(self._finish_close)
        except TypeError:
            pass

    def update_mode_ui(self, mode: AdBlockMode) -> None:
        self.current_mode = mode
        self._update_button_styles()

        shield_color = QColor("#6366F1")
        if mode == AdBlockMode.STRICT:
            shield_color = QColor("#EF4444")
        elif mode == AdBlockMode.DISABLED:
            shield_color = QColor("#71717A")

        self._draw_shield_pixmap(shield_color)

    def update_stats_ui(self, page_ads: int, page_trackers: int, session_ads: int, session_trackers: int) -> None:
        self.lbl_page_ads.setText(str(page_ads))
        self.lbl_page_trackers.setText(str(page_trackers))
        self.lbl_session_ads.setText(str(session_ads))
        self.lbl_session_trackers.setText(str(session_trackers))

    def _update_button_styles(self) -> None:
        active_style = """
            QPushButton {
                background: #6366F1;
                color: #FFFFFF;
                border: 1px solid #818CF8;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11px;
            }
        """
        inactive_style = """
            QPushButton {
                background: #27272A;
                color: #A1A1AA;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #3F3F46;
                color: #F4F4F5;
            }
        """
        self.btn_strict.setStyleSheet(active_style if self.current_mode == AdBlockMode.STRICT else inactive_style)
        self.btn_balanced.setStyleSheet(active_style if self.current_mode == AdBlockMode.BALANCED else inactive_style)
        self.btn_disabled.setStyleSheet(active_style if self.current_mode == AdBlockMode.DISABLED else inactive_style)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_popup()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.card.geometry().contains(event.pos()):
            self.close_popup()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg_color = QColor(
            OVERLAY_BACKDROP_COLOR.red(),
            OVERLAY_BACKDROP_COLOR.green(),
            OVERLAY_BACKDROP_COLOR.blue(),
            int(OVERLAY_BACKDROP_COLOR.alpha() * self._opacity),
        )
        painter.fillRect(self.rect(), bg_color)

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        self.card.setGeometry(self._calculate_card_rect())

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        if watched == self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return super().eventFilter(watched, event)


# ==========================================
# 4 & 5. Extension Architecture & Implementations
# ==========================================

class BrowserExtension(QObject):
    """Abstract Base Class for modular browser extensions."""

    def __init__(self, name: str, extension_id: str, description: str) -> None:
        super().__init__()
        self.name = name
        self.extension_id = extension_id
        self.description = description
        self.enabled = True

    def initialize(self, window: "MainWindow") -> None:
        pass

    def shutdown(self, window: "MainWindow") -> None:
        pass

    def on_page_load(self, view: QWebEngineView, url: QUrl) -> None:
        pass

    def on_tab_created(self, view: QWebEngineView) -> None:
        pass


class ShortsBlockerExtension(BrowserExtension):
    """Automatically redirects YouTube Shorts to standard watch URL and hides Shorts UI shelves."""

    def __init__(self) -> None:
        super().__init__(
            name="YouTube Shorts Blocker",
            extension_id="shorts_blocker",
            description="Redirects youtube.com/shorts/ to youtube.com/watch and hides Shorts shelves."
        )

    def on_page_load(self, view: QWebEngineView, url: QUrl) -> None:
        if not self.enabled:
            return
        url_str = url.toString()
        if "youtube.com/shorts/" in url_str:
            video_id = url_str.split("youtube.com/shorts/")[1].split("?")[0]
            new_url = f"https://www.youtube.com/watch?v={video_id}"
            view.load(QUrl(new_url))

        if "youtube.com" in url_str:
            js_script = """
            (function() {
                var style = document.createElement('style');
                style.innerHTML = 'ytd-rich-section-renderer, ytd-reel-shelf-renderer { display: none !important; }';
                document.head.appendChild(style);
            })();
            """
            view.page().runJavaScript(js_script)


class InspectElementExtension(BrowserExtension):
    """Enables Chromium DevTools inspection on Ctrl+Shift+I or context menu."""

    def __init__(self) -> None:
        super().__init__(
            name="Inspect Element & DevTools",
            extension_id="inspect_element",
            description="Adds Chromium Developer Tools integration and right-click inspect."
        )

    def initialize(self, window: "MainWindow") -> None:
        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+I"), window)
        self.shortcut.activated.connect(lambda: self._open_devtools(window))

    def _open_devtools(self, window: "MainWindow") -> None:
        if not self.enabled:
            return
        browser = window.current_browser()
        if browser:
            if not hasattr(browser, "_devtools_window") or browser._devtools_window is None:
                dev_view = QWebEngineView()
                dev_page = QWebEnginePage(window.profile_manager.web_engine_profile, dev_view)
                dev_view.setPage(dev_page)
                browser.page().setDevToolsPage(dev_page)
                dev_view.setWindowTitle(f"DevTools - {browser.title()}")
                dev_view.resize(1000, 600)
                browser._devtools_window = dev_view
            browser._devtools_window.show()
            browser._devtools_window.raise_()


class DarkReaderLiteExtension(BrowserExtension):
    """Injects high-contrast dark theme CSS into bright websites."""

    DARK_CSS = """
    html {
        background-color: #121214 !important;
        color: #E4E4E7 !important;
        filter: invert(0.9) hue-rotate(180deg) !important;
    }
    img, video, canvas, svg, [style*="background-image"] {
        filter: invert(1.111) hue-rotate(180deg) !important;
    }
    """

    def __init__(self) -> None:
        super().__init__(
            name="Dark Reader Lite",
            extension_id="dark_reader",
            description="Intelligently forces sleek dark mode on light websites."
        )
        self.enabled = False

    def on_page_load(self, view: QWebEngineView, url: QUrl) -> None:
        if self.enabled:
            escaped_css = json.dumps(self.DARK_CSS)
            js = f"""
            (function() {{
                var style = document.getElementById('zenith-dark-reader');
                if (!style) {{
                    style = document.createElement('style');
                    style.id = 'zenith-dark-reader';
                    style.innerHTML = {escaped_css};
                    document.head.appendChild(style);
                }}
            }})();
            """
            view.page().runJavaScript(js)

    def toggle(self, window: "MainWindow") -> None:
        self.enabled = not self.enabled
        for i in range(window.tab_widget.count()):
            widget = window.tab_widget.widget(i)
            if isinstance(widget, QWebEngineView):
                if self.enabled:
                    self.on_page_load(widget, widget.url())
                else:
                    widget.page().runJavaScript("""
                    var style = document.getElementById('zenith-dark-reader');
                    if (style) style.remove();
                    """)


class ReaderModeExtension(BrowserExtension):
    """Distraction-free clutter removal view for news articles and blogs."""

    def __init__(self) -> None:
        super().__init__(
            name="Reader Mode",
            extension_id="reader_mode",
            description="Cleans article clutter into a centered typography reader format."
        )

    def initialize(self, window: "MainWindow") -> None:
        self.shortcut = QShortcut(QKeySequence("Ctrl+Shift+R"), window)
        self.shortcut.activated.connect(lambda: self.toggle_reader_mode(window))

    def toggle_reader_mode(self, window: "MainWindow") -> None:
        if not self.enabled:
            return
        browser = window.current_browser()
        if browser:
            js = """
            (function() {
                var existing = document.getElementById('zenith-reader-frame');
                if (existing) { existing.remove(); return; }

                var article = document.querySelector('article') || document.querySelector('main') || document.body;
                var clone = article.cloneNode(true);

                var container = document.createElement('div');
                container.id = 'zenith-reader-frame';
                container.style.position = 'fixed';
                container.style.top = '0'; container.style.left = '0';
                container.style.width = '100vw'; container.style.height = '100vh';
                container.style.backgroundColor = '#18181B';
                container.style.color = '#F4F4F5';
                container.style.zIndex = '999999';
                container.style.overflowY = 'auto';
                container.style.padding = '40px 20%';
                container.style.fontFamily = 'Georgia, serif';
                container.style.fontSize = '20px';
                container.style.lineHeight = '1.8';

                container.appendChild(clone);
                document.body.appendChild(container);
            })();
            """
            browser.page().runJavaScript(js)


class CookieCleanerExtension(BrowserExtension):
    """Instantly clears website cookies, local storage, cache, and session memory."""

    def __init__(self) -> None:
        super().__init__(
            name="Cookie & Storage Cleaner",
            extension_id="cookie_cleaner",
            description="One-click privacy wipe of browser cookies, cache, and local storage."
        )

    def clear_all_data(self, window: "MainWindow") -> None:
        profile = window.profile_manager.web_engine_profile
        if profile:
            profile.clearHttpCache()
            profile.cookieStore().deleteAllCookies()
            window.statusBar().showMessage("Cleared cache and cookies for current profile.", 3000)


class QuickCommandsExtension(BrowserExtension):
    """Zenith Command palette trigger."""

    def __init__(self) -> None:
        super().__init__(
            name="Quick Commands Palette",
            extension_id="quick_commands",
            description="Universal command search bar."
        )


class ExtensionManager:
    """Central registry and workflow coordinator for extensions."""

    def __init__(self, window: "MainWindow") -> None:
        self.window = window
        self.extensions: Dict[str, BrowserExtension] = {}

        self.register(ShortsBlockerExtension())
        self.register(InspectElementExtension())
        self.register(DarkReaderLiteExtension())
        self.register(ReaderModeExtension())
        self.register(CookieCleanerExtension())
        self.register(QuickCommandsExtension())

    def register(self, extension: BrowserExtension) -> None:
        self.extensions[extension.extension_id] = extension
        extension.initialize(self.window)

    def notify_page_load(self, view: QWebEngineView, url: QUrl) -> None:
        for ext in self.extensions.values():
            if ext.enabled:
                ext.on_page_load(view, url)

    def notify_tab_created(self, view: QWebEngineView) -> None:
        for ext in self.extensions.values():
            if ext.enabled:
                ext.on_tab_created(view)


# ==========================================
# Quick Commands Palette Widget (Ctrl+Shift+P)
# ==========================================

class QuickCommandsPalette(QWidget):
    """Command palette widget matching Spotlight design aesthetics."""

    def __init__(self, parent: "MainWindow") -> None:
        super().__init__(parent)
        self.main_window = parent
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()

        self._opacity = 0.0
        self._scale = 0.95
        self.commands: List[Tuple[str, str, Callable[[], None]]] = []

        self._init_ui()
        self._init_animations()
        self._populate_commands()
        parent.installEventFilter(self)

    def _init_ui(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 50, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.card = QFrame(self)
        self.card.setFixedWidth(580)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(24, 24, 28, 245);
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: {CORNER_RADIUS}px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)

        self.input_field = QLineEdit(self.card)
        self.input_field.setPlaceholderText("Type a command (e.g. New Tab, Switch Profile, Dark Mode)...")
        self.input_field.setFrame(False)
        self.input_field.setFont(QFont("Inter", 12))
        self.input_field.setStyleSheet(f"color: {TEXT_COLOR.name()}; background: transparent;")
        self.input_field.textChanged.connect(self._filter_commands)

        self.list_widget = QListWidget(self.card)
        self.list_widget.setFixedHeight(220)
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: #F4F4F5;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 8px;
            }
            QListWidget::item:hover, QListWidget::item:selected {
                background: #3F3F46;
                color: #FFFFFF;
            }
        """)
        self.list_widget.itemActivated.connect(self._execute_selected)

        card_layout.addWidget(self.input_field)
        card_layout.addWidget(self.list_widget)

        main_layout.addWidget(self.card)

    def _populate_commands(self) -> None:
        mw = self.main_window
        self.commands = [
            ("Switch / Manage Profiles", "Open profile manager window", lambda: mw.open_profile_dialog()),
            ("New Tab", "Open a new blank tab", lambda: mw.add_tab()),
            ("Close Tab", "Close current active tab", lambda: mw._handle_close_shortcut()),
            ("Restore Tab", "Reopen last closed tab", lambda: mw.restore_closed_tab()),
            ("Restore Previous Session", "Restore tabs from previous session", lambda: mw.restore_previous_session()),
            ("Dark Reader", "Toggle Dark Reader Lite", lambda: mw.ext_manager.extensions["dark_reader"].toggle(mw)),
            ("Reader Mode", "Toggle distraction-free reader", lambda: mw.ext_manager.extensions["reader_mode"].toggle_reader_mode(mw)),
            ("Clear Cache & Cookies", "Wipe cookies and site data for current profile", lambda: mw.ext_manager.extensions["cookie_cleaner"].clear_all_data(mw)),
            ("Ad Blocker Settings", "Open shield overlay popup", lambda: mw.ad_block_popup.open_popup()),
            ("Open Settings", "Configure browser options", lambda: mw.open_settings_dialog()),
            ("Downloads Manager", "Show active & finished downloads", lambda: mw.open_downloads_dialog()),
            ("Bookmark Current Page", "Save current URL to profile bookmarks", lambda: mw.bookmark_current_page()),
            ("Bookmark All Tabs", "Save all open tabs", lambda: mw.bookmark_all_tabs()),
            ("Inspect Element", "Open Chromium Developer Tools", lambda: mw.ext_manager.extensions["inspect_element"]._open_devtools(mw)),
        ]
        self._filter_commands("")

    def _filter_commands(self, text: str) -> None:
        self.list_widget.clear()
        query = text.lower().strip()
        for title, desc, action in self.commands:
            if not query or query in title.lower() or query in desc.lower():
                item = QListWidgetItem(f"⚡ {title} — {desc}")
                item.setData(Qt.ItemDataRole.UserRole, action)
                self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _execute_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            action = item.data(Qt.ItemDataRole.UserRole)
            self.close_palette()
            if callable(action):
                action()

    def _init_animations(self) -> None:
        self.fade_anim = QPropertyAnimation(self, b"overlayOpacity")
        self.fade_anim.setDuration(ANIMATION_DURATION_MS)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.scale_anim = QPropertyAnimation(self, b"overlayScale")
        self.scale_anim.setDuration(ANIMATION_DURATION_MS)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.fade_anim)
        self.anim_group.addAnimation(self.scale_anim)

    @pyqtProperty(float)
    def overlayOpacity(self) -> float:
        return self._opacity

    @overlayOpacity.setter
    def overlayOpacity(self, val: float) -> None:
        self._opacity = val
        self.update()

    @pyqtProperty(float)
    def overlayScale(self) -> float:
        return self._scale

    @overlayScale.setter
    def overlayScale(self, val: float) -> None:
        self._scale = val
        self.card.setGeometry(self._calculate_card_rect())
        self.update()

    def _calculate_card_rect(self) -> QRect:
        base_w, base_h = 580, self.card.sizeHint().height()
        w = int(base_w * self._scale)
        h = int(base_h * self._scale)
        x = (self.width() - w) // 2
        y = int(50 * self._scale)
        return QRect(x, y, w, h)

    def open_palette(self) -> None:
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self.input_field.setFocus()
        self.input_field.selectAll()

        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.scale_anim.setStartValue(0.95)
        self.scale_anim.setEndValue(1.0)
        self.anim_group.stop()
        self.anim_group.start()

    def close_palette(self) -> None:
        self.fade_anim.setStartValue(self._opacity)
        self.fade_anim.setEndValue(0.0)
        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(0.95)
        self.anim_group.stop()
        try:
            self.anim_group.finished.disconnect()
        except TypeError:
            pass
        self.anim_group.finished.connect(self.hide)
        self.anim_group.start()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_palette()
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._execute_selected()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.card.geometry().contains(event.pos()):
            self.close_palette()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        bg = QColor(0, 0, 0, int(160 * self._opacity))
        painter.fillRect(self.rect(), bg)


# ==========================================
# 7. Downloads Manager (Ctrl+J)
# ==========================================

class DownloadsDialog(QDialog):
    """Arc-styled floating Download Manager with live progress updates."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Downloads Manager")
        self.resize(650, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #18181B;
                color: #F4F4F5;
            }
            QTableWidget {
                background-color: #1C1C20;
                border: 1px solid #27272A;
                border-radius: 8px;
                gridline-color: #27272A;
                color: #F4F4F5;
            }
            QHeaderView::section {
                background-color: #27272A;
                color: #A1A1AA;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("Downloads", self)
        title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["Filename", "Progress", "Speed/State", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 140)
        layout.addWidget(self.table)

        self.download_items: Dict[QWebEngineDownloadRequest, int] = {}

    def add_download(self, item: QWebEngineDownloadRequest) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        file_name = os.path.basename(item.downloadDirectory() + "/" + item.downloadFileName())
        self.table.setItem(row, 0, QTableWidgetItem(file_name))

        pbar = QProgressBar()
        pbar.setRange(0, 100)
        pbar.setFixedHeight(14)
        pbar.setStyleSheet("QProgressBar::chunk { background-color: #6366F1; }")
        self.table.setCellWidget(row, 1, pbar)

        state_item = QTableWidgetItem("Downloading...")
        self.table.setItem(row, 2, state_item)

        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background: #3F3F46; color: white; border-radius: 4px; font-size: 10px;")
        btn_cancel.clicked.connect(item.cancel)
        btn_layout.addWidget(btn_cancel)
        self.table.setCellWidget(row, 3, btn_container)

        self.download_items[item] = row

        item.receivedBytesChanged.connect(lambda: self._update_progress(item))
        item.isFinishedChanged.connect(lambda: self._on_finished(item))

    def _update_progress(self, item: QWebEngineDownloadRequest) -> None:
        if item in self.download_items:
            row = self.download_items[item]
            total = item.totalBytes()
            received = item.receivedBytes()
            if total > 0:
                pct = int((received / total) * 100)
                pbar = self.table.cellWidget(row, 1)
                if isinstance(pbar, QProgressBar):
                    pbar.setValue(pct)

    def _on_finished(self, item: QWebEngineDownloadRequest) -> None:
        if item in self.download_items:
            row = self.download_items[item]
            state_item = self.table.item(row, 2)
            if state_item:
                state_item.setText("Completed" if item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted else "Cancelled")


# ==========================================
# 8. Modern Settings Dialog (Ctrl+,)
# ==========================================

class SettingsDialog(QDialog):
    """Comprehensive Preferences Dialog with responsive profile integration."""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("Zenith Settings")
        self.resize(700, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #18181B;
                color: #F4F4F5;
            }
            QTabWidget::pane {
                border: 1px solid #27272A;
                background-color: #1C1C20;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #27272A;
                color: #A1A1AA;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #6366F1;
                color: #FFFFFF;
            }
            QLabel {
                color: #F4F4F5;
                font-size: 12px;
            }
            QLineEdit, QComboBox {
                background: #27272A;
                color: #F4F4F5;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)

        tabs = QTabWidget(self)
        settings_data = main_window.profile_manager.data_manager.load_settings()

        # General Tab
        gen_widget = QWidget()
        gen_layout = QVBoxLayout(gen_widget)

        gen_layout.addWidget(QLabel("Default Search Engine:"))
        self.combo_engine = QComboBox()
        self.combo_engine.addItems(list(SEARCH_ENGINES.keys()))
        self.combo_engine.setCurrentText(settings_data.get("search_engine", DEFAULT_ENGINE))
        gen_layout.addWidget(self.combo_engine)

        gen_layout.addWidget(QLabel("Homepage URL:"))
        self.edit_home = QLineEdit(settings_data.get("homepage", HOME_PAGE_FILE))
        gen_layout.addWidget(self.edit_home)

        self.chk_restore = QCheckBox("Restore previous session on startup")
        self.chk_restore.setChecked(settings_data.get("restore_session", True))
        self.chk_restore.setStyleSheet("color: #F4F4F5; margin-top: 10px;")
        gen_layout.addWidget(self.chk_restore)

        btn_clear_cache = QPushButton("Clear Cache for Current Profile")
        btn_clear_cache.setStyleSheet("background: #27272A; border: 1px solid #3F3F46; color: white; padding: 6px; border-radius: 4px; max-width: 240px; margin-top: 10px;")
        btn_clear_cache.clicked.connect(self._clear_cache)
        gen_layout.addWidget(btn_clear_cache)

        gen_layout.addStretch()
        tabs.addTab(gen_widget, "General")

        # Shield / AdBlocker Tab
        shield_widget = QWidget()
        shield_layout = QVBoxLayout(shield_widget)

        shield_layout.addWidget(QLabel("Default Ad Blocker Mode:"))
        self.combo_admode = QComboBox()
        self.combo_admode.addItems(["Strict", "Balanced", "Disabled"])
        self.combo_admode.setCurrentText(main_window.ad_blocker.mode.value)
        shield_layout.addWidget(self.combo_admode)

        shield_layout.addWidget(QLabel("Active Filter Lists:"))
        for name, info in main_window.ad_blocker.filter_lists.items():
            cb = QCheckBox(f"{name} ({info.rules_count} rules)")
            cb.setChecked(info.enabled)
            cb.setStyleSheet("color: #F4F4F5;")
            cb.toggled.connect(lambda chk, n=name: main_window.ad_blocker.set_filter_enabled(n, chk))
            shield_layout.addWidget(cb)

        shield_layout.addStretch()
        tabs.addTab(shield_widget, "Shield & AdBlock")

        # Extensions Tab
        ext_widget = QWidget()
        ext_layout = QVBoxLayout(ext_widget)
        ext_layout.addWidget(QLabel("Manage Extensions:"))

        for ext_id, ext in main_window.ext_manager.extensions.items():
            cb = QCheckBox(f"{ext.name} — {ext.description}")
            cb.setChecked(ext.enabled)
            cb.setStyleSheet("color: #F4F4F5;")
            cb.toggled.connect(lambda chk, e=ext: setattr(e, "enabled", chk))
            ext_layout.addWidget(cb)

        ext_layout.addStretch()
        tabs.addTab(ext_widget, "Extensions")

        layout.addWidget(tabs)

        btn_save = QPushButton("Save & Apply")
        btn_save.setFixedHeight(34)
        btn_save.setStyleSheet("background: #6366F1; color: white; border-radius: 6px; font-weight: bold;")
        btn_save.clicked.connect(self._save_settings)
        layout.addWidget(btn_save)

    def _clear_cache(self) -> None:
        if self.main_window.profile_manager.web_engine_profile:
            self.main_window.profile_manager.web_engine_profile.clearHttpCache()
            QMessageBox.information(self, "Cache Cleared", "HTTP Cache cleared successfully.")

    def _save_settings(self) -> None:
        new_mode_str = self.combo_admode.currentText()
        self.main_window.ad_blocker.set_mode(AdBlockMode(new_mode_str))
        
        settings = self.main_window.profile_manager.data_manager.load_settings()
        settings["search_engine"] = self.combo_engine.currentText()
        settings["homepage"] = self.edit_home.text().strip()
        settings["restore_session"] = self.chk_restore.isChecked()
        settings["ad_blocker_mode"] = new_mode_str
        
        self.main_window.profile_manager.data_manager.save_settings(settings)
        self.accept()


# ==========================================
# Original Search Overlay Widgets
# ==========================================

class SearchIconLabel(QLabel):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(20, 20)

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(ICON_COLOR, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(2, 2, 11, 11)
        painter.drawLine(11, 11, 17, 17)


class SearchLineEdit(QLineEdit):
    escape_pressed = pyqtSignal()
    submit_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("Search, enter a URL, or use prefixes (g, d, b, gh, yt, r)...")
        self.setFrame(False)
        self.setFont(QFont("Inter", 13))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            text = self.text().strip()
            if text:
                self.submit_requested.emit(text)
            event.accept()
        else:
            super().keyPressEvent(event)


class SpotlightCard(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.is_focused = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("SpotlightCard")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 10)
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(12)

        self.icon_label = SearchIconLabel(self)
        self.input_field = SearchLineEdit(self)

        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.input_field, 1, Qt.AlignmentFlag.AlignVCenter)

    def set_focused_state(self, focused: bool) -> None:
        self.is_focused = focused
        self.update()

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        rect = QRectF(self.rect().adjusted(1, 1, -1, -1))
        path.addRoundedRect(rect, float(CORNER_RADIUS), float(CORNER_RADIUS))
        painter.fillPath(path, CARD_BG_COLOR)
        border_color = CARD_BORDER_FOCUS_COLOR if self.is_focused else CARD_BORDER_COLOR
        painter.setPen(QPen(border_color, 1.5 if self.is_focused else 1.0))
        painter.drawPath(path)


class SpotlightOverlay(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.hide()

        self._opacity = 0.0
        self._scale = 0.95

        self._init_ui()
        self._init_animations()

        self.card.input_field.escape_pressed.connect(self.close_overlay)
        self.card.input_field.submit_requested.connect(self._handle_submit)
        parent.installEventFilter(self)

    def _init_ui(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 60, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.card = SpotlightCard(self)
        self.card.setFixedWidth(640)
        self.card.setFixedHeight(54)
        main_layout.addWidget(self.card)

        self.card.input_field.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {TEXT_COLOR.name()};
                selection-background-color: #4F46E5;
                selection-color: #FFFFFF;
            }}
            QLineEdit::placeholder {{
                color: {PLACEHOLDER_COLOR.name()};
            }}
        """)

    def _init_animations(self) -> None:
        self.fade_anim = QPropertyAnimation(self, b"overlayOpacity")
        self.fade_anim.setDuration(ANIMATION_DURATION_MS)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.scale_anim = QPropertyAnimation(self, b"overlayScale")
        self.scale_anim.setDuration(ANIMATION_DURATION_MS)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.fade_anim)
        self.anim_group.addAnimation(self.scale_anim)

    @pyqtProperty(float)
    def overlayOpacity(self) -> float:
        return self._opacity

    @overlayOpacity.setter
    def overlayOpacity(self, val: float) -> None:
        self._opacity = val
        self.update()

    @pyqtProperty(float)
    def overlayScale(self) -> float:
        return self._scale

    @overlayScale.setter
    def overlayScale(self, val: float) -> None:
        self._scale = val
        self.card.setGeometry(self._calculate_card_rect())
        self.update()

    def _calculate_card_rect(self) -> QRect:
        base_w, base_h = 640, 54
        w = int(base_w * self._scale)
        h = int(base_h * self._scale)
        x = (self.width() - w) // 2
        y = int(60 * self._scale)
        return QRect(x, y, w, h)

    def open_overlay(self) -> None:
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()

        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.scale_anim.setStartValue(0.95)
        self.scale_anim.setEndValue(1.0)

        self.anim_group.stop()
        self.anim_group.start()

        self.card.input_field.setFocus()
        self.card.input_field.selectAll()
        self.card.set_focused_state(True)

    def close_overlay(self) -> None:
        self.fade_anim.setStartValue(self._opacity)
        self.fade_anim.setEndValue(0.0)
        self.scale_anim.setStartValue(self._scale)
        self.scale_anim.setEndValue(0.95)

        self.anim_group.stop()
        try:
            self.anim_group.finished.disconnect()
        except TypeError:
            pass
        self.anim_group.finished.connect(self._finish_close)
        self.anim_group.start()

    def _finish_close(self) -> None:
        self.hide()
        self.card.set_focused_state(False)
        try:
            self.anim_group.finished.disconnect(self._finish_close)
        except TypeError:
            pass

    def _handle_submit(self, query: str) -> None:
        self.close_overlay()
        self.navigate_requested.emit(query)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self.card.geometry().contains(event.pos()):
            self.close_overlay()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        bg_color = QColor(
            OVERLAY_BACKDROP_COLOR.red(),
            OVERLAY_BACKDROP_COLOR.green(),
            OVERLAY_BACKDROP_COLOR.blue(),
            int(OVERLAY_BACKDROP_COLOR.alpha() * self._opacity),
        )
        painter.fillRect(self.rect(), bg_color)

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        self.card.setGeometry(self._calculate_card_rect())

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        if watched == self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.setGeometry(self.parentWidget().rect())
        return super().eventFilter(watched, event)


# ==========================================
# 10. UI Polish - Rounded Custom TabBar
# ==========================================

class CustomTabBar(QTabBar):
    new_tab_requested = pyqtSignal()
    middle_click_closed = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setElideMode(Qt.TextElideMode.ElideRight)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            index = self.tabAt(event.pos())
            if index != -1:
                self.middle_click_closed.emit(index)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.tabAt(event.pos()) == -1:
                self.new_tab_requested.emit()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)


class BrowserTabWidget(QTabWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        custom_tab_bar = CustomTabBar(self)
        self.setTabBar(custom_tab_bar)
        self.setMovable(True)
        self.setTabsClosable(True)

        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #121214;
            }
            QTabBar {
                background-color: #18181B;
                border-bottom: 1px solid #27272A;
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                background: #1C1C20;
                color: #A1A1AA;
                border: 1px solid #27272A;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 7px 16px;
                margin-top: 5px;
                margin-right: 3px;
                min-width: 130px;
                max-width: 230px;
                font-family: 'Inter', sans-serif;
                font-size: 11px;
            }
            QTabBar::tab:hover {
                background: #27272A;
                color: #F4F4F5;
            }
            QTabBar::tab:selected {
                background: #27272A;
                color: #FFFFFF;
                border: 1px solid #3F3F46;
                border-bottom: 2px solid #6366F1;
            }
        """)

        custom_tab_bar.new_tab_requested.connect(self._on_new_tab_requested)
        custom_tab_bar.middle_click_closed.connect(self.tabCloseRequested.emit)

    def _on_new_tab_requested(self) -> None:
        window = self.window()
        if isinstance(window, MainWindow):
            window.add_tab()


# ==========================================
# Main Application Window Architecture
# ==========================================

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(DEFAULT_WINDOW_SIZE)

        # 1. Profile Architecture Initialization
        self.profile_manager = ProfileManager(base_dir="profiles")
        self.session_manager = SessionManager(self.profile_manager)

        self.quick_palette = QuickCommandsPalette(self)
        self.default_icon = self._create_default_icon()
        self.help_icon = self._create_help_icon()
        self.closed_tabs_history: List[Tuple[QUrl, str]] = []

        self._init_ad_blocker()
        self._init_browser_ui()
        self._init_extensions()
        self._init_status_bar()
        self._init_overlays()
        self._init_shortcuts()

        # 2. Startup session load logic
        settings = self.profile_manager.data_manager.load_settings()
        if settings.get("restore_session", True):
            if not self.restore_previous_session():
                self.add_tab()
        else:
            self.add_tab()

    def _init_ad_blocker(self) -> None:
        self.ad_blocker = AdBlocker(self)
        if self.profile_manager.web_engine_profile:
            self.profile_manager.web_engine_profile.setUrlRequestInterceptor(self.ad_blocker)

        settings = self.profile_manager.data_manager.load_settings()
        saved_mode_str = settings.get("ad_blocker_mode", AdBlockMode.BALANCED.value)
        try:
            saved_mode = AdBlockMode(saved_mode_str)
        except ValueError:
            saved_mode = AdBlockMode.BALANCED

        self.ad_blocker.set_mode(saved_mode)
        self.ad_blocker.stats_updated.connect(self._update_ad_block_ui)

    def _init_browser_ui(self) -> None:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Navigation Toolbar
        self.toolbar = QFrame(self)
        self.toolbar.setFixedHeight(40)
        self.toolbar.setStyleSheet("""
            QFrame {
                background-color: #18181B;
                border-bottom: 1px solid #27272A;
            }
            QPushButton {
                background: #27272A;
                color: #F4F4F5;
                border: 1px solid #3F3F46;
                border-radius: 8px;
                min-width: 28px;
                max-width: 28px;
                min-height: 24px;
                max-height: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #3F3F46;
                color: #FFFFFF;
            }
            QPushButton:disabled {
                background: #1C1C20;
                color: #52525B;
                border: 1px solid #27272A;
            }
            QPushButton#ProfileBtn {
                min-width: 110px;
                max-width: 180px;
                padding-left: 8px;
                padding-right: 8px;
                text-align: left;
            }
        """)

        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(10, 0, 10, 0)
        tb_layout.setSpacing(8)

        self.btn_back = QPushButton("◀", self.toolbar)
        self.btn_back.setToolTip("Back (Alt+Left)")
        self.btn_back.clicked.connect(self._nav_back)

        self.btn_forward = QPushButton("▶", self.toolbar)
        self.btn_forward.setToolTip("Forward (Alt+Right)")
        self.btn_forward.clicked.connect(self._nav_forward)

        self.btn_reload = QPushButton("↻", self.toolbar)
        self.btn_reload.setToolTip("Reload (Ctrl+R)")
        self.btn_reload.clicked.connect(self._nav_reload)

        self.btn_profile = QPushButton("", self.toolbar)
        self.btn_profile.setObjectName("ProfileBtn")
        self.btn_profile.setToolTip("Switch / Manage Profiles (Ctrl+Shift+P)")
        self.btn_profile.clicked.connect(self.open_profile_dialog)
        self._update_profile_button_ui()

        tb_layout.addWidget(self.btn_back)
        tb_layout.addWidget(self.btn_forward)
        tb_layout.addWidget(self.btn_reload)
        tb_layout.addStretch()
        tb_layout.addWidget(self.btn_profile)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: transparent;
            }
            QProgressBar::chunk {
                background-color: #6366F1;
            }
        """)

        self.tab_widget = BrowserTabWidget(self)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.tab_widget)
        layout.addWidget(self.progress_bar)
        self.setCentralWidget(container)

        # Profile Download Handler
        if self.profile_manager.web_engine_profile:
            self.profile_manager.web_engine_profile.downloadRequested.connect(self._on_download_requested)
        self.downloads_dialog = DownloadsDialog(self)

    def _update_profile_button_ui(self) -> None:
        curr = self.profile_manager.active_profile
        if curr:
            self.btn_profile.setText(f"{curr.avatar} {curr.name}")

    def _init_extensions(self) -> None:
        self.ext_manager = ExtensionManager(self)

    def _init_overlays(self) -> None:
        self.overlay = SpotlightOverlay(self)
        self.overlay.navigate_requested.connect(self.navigate)

        self.ad_block_popup = AdBlockPopup(self)
        self.ad_block_popup.mode_changed.connect(self._change_ad_block_mode)
        self.ad_block_popup.reset_stats_requested.connect(self.ad_blocker.reset_stats)

    def _init_status_bar(self) -> None:
        status_container = QWidget(self)
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(12, 4, 12, 4)

        self.status_adblock_label = QLabel(status_container)
        self.status_adblock_label.setStyleSheet("color: #A1A1AA; font-size: 11px; font-weight: bold;")
        self.status_adblock_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_adblock_label.mousePressEvent = lambda e: self.ad_block_popup.open_popup()

        status_layout.addStretch()
        status_layout.addWidget(self.status_adblock_label)

        self.statusBar().addPermanentWidget(status_container)
        self.statusBar().setStyleSheet("QStatusBar { background: #18181B; border-top: 1px solid #27272A; }")

    def _init_shortcuts(self) -> None:
        # Alt+Left & Alt+Right for Navigation
        shortcut_back = QShortcut(QKeySequence("Alt+Left"), self)
        shortcut_back.activated.connect(self._nav_back)

        shortcut_fwd = QShortcut(QKeySequence("Alt+Right"), self)
        shortcut_fwd.activated.connect(self._nav_forward)

        # Profile Switcher Shortcut
        QShortcut(QKeySequence("Ctrl+Shift+P"), self).activated.connect(self.open_profile_dialog)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.restore_previous_session)

        # Navigation Shortcuts
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self.overlay.open_overlay)
        QShortcut(QKeySequence("Alt+T"), self).activated.connect(self.overlay.open_overlay)
        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(self.overlay.open_overlay)

        QShortcut(QKeySequence("Ctrl+Shift+A"), self).activated.connect(self.ad_block_popup.open_popup)
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(lambda: self.add_tab())
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self._handle_close_shortcut)

        QShortcut(QKeySequence("Ctrl+Shift+T"), self).activated.connect(self.restore_closed_tab)
        QShortcut(QKeySequence("Ctrl+Tab"), self).activated.connect(self._next_tab)
        QShortcut(QKeySequence("Ctrl+PageDown"), self).activated.connect(self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self).activated.connect(self._prev_tab)
        QShortcut(QKeySequence("Ctrl+PageUp"), self).activated.connect(self._prev_tab)

        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._nav_reload)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self).activated.connect(self._hard_reload)
        QShortcut(QKeySequence("Alt+Home"), self).activated.connect(lambda: self.current_browser().load(self._get_initial_url()) if self.current_browser() else None)

        # Downloads & Settings Shortcuts
        QShortcut(QKeySequence("Ctrl+J"), self).activated.connect(self.open_downloads_dialog)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self.open_settings_dialog)

        # Bookmarks Shortcuts
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self.bookmark_current_page)
        QShortcut(QKeySequence("Ctrl+Shift+D"), self).activated.connect(self.bookmark_all_tabs)

        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(self.open_help)

        # Direct tab switching
        for i in range(1, 9):
            shortcut_num = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            shortcut_num.activated.connect(lambda idx=i - 1: self.switch_to_tab(idx))

    def current_browser(self) -> Optional[CustomWebEngineView]:
        widget = self.tab_widget.currentWidget()
        if isinstance(widget, CustomWebEngineView):
            return widget
        return None

    def add_tab(self, url: Optional[QUrl] = None, title: str = "New Tab", icon: Optional[QIcon] = None) -> int:
        view = CustomWebEngineView(self.profile_manager.web_engine_profile, self)
        tab_icon = icon if icon else self.default_icon

        script = QWebEngineScript()
        script.setSourceCode(f"var style = document.createElement('style'); style.innerHTML = `{MODERN_SCROLLBAR_CSS}`; document.head.appendChild(style);")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        view.page().scripts().insert(script)

        index = self.tab_widget.addTab(view, tab_icon, title)

        view.titleChanged.connect(lambda title_text, v=view: self.update_tab_title(v, title_text))
        view.iconChanged.connect(lambda icon_obj, v=view: self.update_tab_icon(v, icon_obj))
        view.loadStarted.connect(lambda v=view: self._on_load_started(v))
        view.loadProgress.connect(lambda progress, v=view: self._on_load_progress(v, progress))
        view.urlChanged.connect(lambda u, v=view: self._on_url_changed(v, u))

        self.ext_manager.notify_tab_created(view)
        self.tab_widget.setCurrentIndex(index)

        if url is None:
            url = self._get_initial_url()

        view.load(url)
        self.update_nav_buttons()
        return index

    def _on_url_changed(self, view: CustomWebEngineView, url: QUrl) -> None:
        url_str = url.toString()
        if url_str and not url_str.startswith("about:"):
            view.custom_history_stack.append(url_str)
            if self.profile_manager.data_manager:
                self.profile_manager.data_manager.add_history_entry(view.title(), url_str)

        self.ext_manager.notify_page_load(view, url)
        self._update_ad_block_ui()
        self.update_nav_buttons()

    def update_nav_buttons(self) -> None:
        browser = self.current_browser()
        if browser and browser.history():
            self.btn_back.setEnabled(browser.history().canGoBack())
            self.btn_forward.setEnabled(browser.history().canGoForward())
        else:
            self.btn_back.setEnabled(False)
            self.btn_forward.setEnabled(False)

    def _nav_back(self) -> None:
        browser = self.current_browser()
        if browser and browser.history().canGoBack():
            browser.back()

    def _nav_forward(self) -> None:
        browser = self.current_browser()
        if browser and browser.history().canGoForward():
            browser.forward()

    def _nav_reload(self) -> None:
        browser = self.current_browser()
        if browser:
            browser.reload()

    def close_tab(self, index: int) -> None:
        if index < 0 or index >= self.tab_widget.count():
            return

        view = self.tab_widget.widget(index)
        if isinstance(view, CustomWebEngineView):
            self.closed_tabs_history.append((view.url(), view.title()))
            try:
                view.titleChanged.disconnect()
                view.iconChanged.disconnect()
                view.loadStarted.disconnect()
                view.loadProgress.disconnect()
            except TypeError:
                pass

        if self.tab_widget.count() == 1:
            if isinstance(view, CustomWebEngineView):
                view.load(self._get_initial_url())
            return

        self.tab_widget.removeTab(index)
        if view:
            view.deleteLater()

    def restore_closed_tab(self) -> None:
        if self.closed_tabs_history:
            url, title = self.closed_tabs_history.pop()
            self.add_tab(url=url, title=title)

    def restore_previous_session(self) -> bool:
        session = self.session_manager.load_session()
        if not session or "tabs" not in session or not session["tabs"]:
            return False

        # Clear active default tabs
        while self.tab_widget.count() > 0:
            w = self.tab_widget.widget(0)
            self.tab_widget.removeTab(0)
            w.deleteLater()

        for tab_info in session["tabs"]:
            url = QUrl(tab_info.get("url", ""))
            title = tab_info.get("title", "Restored Tab")
            idx = self.add_tab(url=url, title=title)
            view = self.tab_widget.widget(idx)
            if isinstance(view, CustomWebEngineView) and "history" in tab_info:
                view.import_history_data(tab_info["history"])

        active_idx = session.get("active_tab", 0)
        if 0 <= active_idx < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(active_idx)

        self.statusBar().showMessage("Restored previous session successfully.", 3000)
        return True

    def open_profile_dialog(self) -> None:
        dlg = ProfileSelectorDialog(self.profile_manager, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.action_taken == "switch":
            if dlg.selected_profile_name:
                self.switch_profile(dlg.selected_profile_name)
        elif dlg.action_taken == "reload":
            self._update_profile_button_ui()

    def switch_profile(self, profile_name: str) -> None:
        self.session_manager.save_session(self)
        self.profile_manager.load_profile(profile_name)
        self._update_profile_button_ui()

        # Reconfigure URL Interceptor
        if self.profile_manager.web_engine_profile:
            self.profile_manager.web_engine_profile.setUrlRequestInterceptor(self.ad_blocker)
            self.profile_manager.web_engine_profile.downloadRequested.connect(self._on_download_requested)

        # Reload or restore session for new profile
        settings = self.profile_manager.data_manager.load_settings()
        if settings.get("restore_session", True):
            if not self.restore_previous_session():
                self._reset_tabs_to_homepage()
        else:
            self._reset_tabs_to_homepage()

    def _reset_tabs_to_homepage(self) -> None:
        while self.tab_widget.count() > 0:
            w = self.tab_widget.widget(0)
            self.tab_widget.removeTab(0)
            w.deleteLater()
        self.add_tab()

    def bookmark_current_page(self) -> None:
        browser = self.current_browser()
        if browser and self.profile_manager.data_manager:
            bookmarks = self.profile_manager.data_manager.load_bookmarks()
            bookmarks.append({
                "title": browser.title(),
                "url": browser.url().toString(),
                "created": datetime.now().isoformat()
            })
            self.profile_manager.data_manager.save_bookmarks(bookmarks)
            self.statusBar().showMessage(f"Bookmarked: {browser.title()}", 3000)

    def bookmark_all_tabs(self) -> None:
        if not self.profile_manager.data_manager:
            return
        bookmarks = self.profile_manager.data_manager.load_bookmarks()
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, CustomWebEngineView):
                bookmarks.append({
                    "title": widget.title(),
                    "url": widget.url().toString(),
                    "created": datetime.now().isoformat()
                })
        self.profile_manager.data_manager.save_bookmarks(bookmarks)
        self.statusBar().showMessage("Bookmarked all active tabs!", 3000)

    def open_downloads_dialog(self) -> None:
        self.downloads_dialog.show()
        self.downloads_dialog.raise_()

    def open_settings_dialog(self) -> None:
        dlg = SettingsDialog(self)
        dlg.exec()

    def _on_download_requested(self, item: QWebEngineDownloadRequest) -> None:
        item.accept()
        if self.profile_manager.data_manager:
            self.profile_manager.data_manager.add_download_entry(
                item.downloadFileName(),
                item.downloadDirectory(),
                item.totalBytes()
            )
        self.downloads_dialog.add_download(item)
        self.open_downloads_dialog()

    def _change_ad_block_mode(self, mode: AdBlockMode) -> None:
        self.ad_blocker.set_mode(mode)
        if self.profile_manager.data_manager:
            settings = self.profile_manager.data_manager.load_settings()
            settings["ad_blocker_mode"] = mode.value
            self.profile_manager.data_manager.save_settings(settings)

    def _update_ad_block_ui(self) -> None:
        mode = self.ad_blocker.mode
        if mode == AdBlockMode.STRICT:
            self.status_adblock_label.setText("🛡 Strict")
        elif mode == AdBlockMode.BALANCED:
            self.status_adblock_label.setText("🛡 Balanced")
        else:
            self.status_adblock_label.setText("⚪ Disabled")

        if self.ad_block_popup.isVisible():
            self.ad_block_popup.update_mode_ui(mode)
            current_view = self.current_browser()
            current_url = current_view.url().toString() if current_view else ""
            p_ads, p_trackers = self.ad_blocker.get_page_stats(current_url)
            self.ad_block_popup.update_stats_ui(
                p_ads, p_trackers,
                self.ad_blocker.session_ads_blocked,
                self.ad_blocker.session_trackers_blocked
            )

    def switch_to_tab(self, index: int) -> None:
        if 0 <= index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)

    def update_tab_title(self, view: CustomWebEngineView, title: str) -> None:
        index = self.tab_widget.indexOf(view)
        if index != -1:
            display_title = title if title.strip() else "New Tab"
            self.tab_widget.setTabText(index, display_title)
            if view == self.current_browser():
                curr = self.profile_manager.active_profile
                prof_str = f" [{curr.name}]" if curr else ""
                self.setWindowTitle(f"{display_title}{prof_str} - {WINDOW_TITLE}")

    def update_tab_icon(self, view: CustomWebEngineView, icon: QIcon) -> None:
        index = self.tab_widget.indexOf(view)
        if index != -1:
            tab_icon = icon if not icon.isNull() else self.default_icon
            self.tab_widget.setTabIcon(index, tab_icon)

    def _on_load_started(self, view: CustomWebEngineView) -> None:
        if view == self.current_browser():
            self.progress_bar.setValue(0)
            self.progress_bar.show()

    def _on_load_progress(self, view: CustomWebEngineView, progress: int) -> None:
        if view == self.current_browser():
            if progress < 100:
                self.progress_bar.setValue(progress)
                self.progress_bar.show()
            else:
                self.progress_bar.hide()
            self.update_nav_buttons()

    def _on_tab_changed(self, index: int) -> None:
        view = self.current_browser()
        if view:
            curr = self.profile_manager.active_profile
            prof_str = f" [{curr.name}]" if curr else ""
            self.setWindowTitle(f"{view.title()}{prof_str} - {WINDOW_TITLE}")
            self.progress_bar.hide()
            self._update_ad_block_ui()
            self.update_nav_buttons()

    def _get_initial_url(self) -> QUrl:
        settings = self.profile_manager.data_manager.load_settings() if self.profile_manager.data_manager else {}
        home = settings.get("homepage", HOME_PAGE_FILE)
        if os.path.exists(home):
            return QUrl.fromLocalFile(os.path.abspath(home))
        engine = settings.get("search_engine", DEFAULT_ENGINE)
        return QUrl(SEARCH_ENGINES.get(engine, SEARCH_ENGINES[DEFAULT_ENGINE]).format(""))

    def _handle_close_shortcut(self) -> None:
        idx = self.tab_widget.currentIndex()
        if idx != -1:
            self.close_tab(idx)

    def _next_tab(self) -> None:
        cnt = self.tab_widget.count()
        if cnt > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() + 1) % cnt)

    def _prev_tab(self) -> None:
        cnt = self.tab_widget.count()
        if cnt > 1:
            self.tab_widget.setCurrentIndex((self.tab_widget.currentIndex() - 1 + cnt) % cnt)

    def navigate(self, input_text: str) -> None:
        input_text = input_text.strip()
        if not input_text:
            return
        browser = self.current_browser()
        if browser:
            browser.load(self._resolve_input_to_url(input_text))

    def _resolve_input_to_url(self, input_text: str) -> QUrl:
        parts = input_text.split(maxsplit=1)
        if len(parts) == 2 and parts[0] in ENGINE_PREFIXES:
            prefix, query = parts[0], parts[1]
            template = SEARCH_ENGINES.get(ENGINE_PREFIXES[prefix], SEARCH_ENGINES[DEFAULT_ENGINE])
            return QUrl(template.format(QUrl.toPercentEncoding(query).data().decode("utf-8")))

        user_url = QUrl.fromUserInput(input_text)
        if user_url.isValid() and "." in input_text and " " not in input_text:
            return user_url

        settings = self.profile_manager.data_manager.load_settings() if self.profile_manager.data_manager else {}
        engine = settings.get("search_engine", DEFAULT_ENGINE)
        template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES[DEFAULT_ENGINE])
        return QUrl(template.format(QUrl.toPercentEncoding(input_text).data().decode("utf-8")))

    def open_help(self) -> None:
        if os.path.exists(HELP_PAGE_FILE):
            self.add_tab(url=QUrl.fromLocalFile(os.path.abspath(HELP_PAGE_FILE)), title="Help", icon=self.help_icon)

    def _hard_reload(self) -> None:
        browser = self.current_browser()
        if browser:
            browser.page().triggerAction(QWebEnginePage.WebAction.ReloadAndBypassCache)

    def closeEvent(self, event: QEvent) -> None:
        self.session_manager.save_session(self)
        super().closeEvent(event)

    def _create_default_icon(self) -> QIcon:
        pix = QPixmap(16, 16)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#A1A1AA"), 1.5))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        return QIcon(pix)

    def _create_help_icon(self) -> QIcon:
        pix = QPixmap(16, 16)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#6366F1"), 1.5))
        painter.drawEllipse(2, 2, 12, 12)
        painter.drawText(QRectF(2, 2, 12, 12), Qt.AlignmentFlag.AlignCenter, "?")
        painter.end()
        return QIcon(pix)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    app.setWindowIcon(QIcon("logo.ico"))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()