"""macOS menu bar entry point for Myorii."""

from __future__ import annotations

from pathlib import Path
import sys

from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSImageLeft,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSStatusBar,
)
from PyObjCTools import AppHelper
import rumps


STATUS_ITEM_LENGTH = 30
STATUS_ICON_SIZE = 30


def _resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    return Path(__file__).resolve().parents[2]


MENUBAR_ICON_PATH = _resource_root() / "assets" / "icons" / "menubar_icon.png"


class MyoriiMenuBarDelegate(NSObject):
    """Creates and owns the macOS status bar item."""

    status_item = None

    def applicationDidFinishLaunching_(self, notification) -> None:
        self._create_status_item()

    def _create_status_item(self) -> None:
        if not MENUBAR_ICON_PATH.exists():
            raise FileNotFoundError(f"Menu bar icon not found: {MENUBAR_ICON_PATH}")

        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            STATUS_ITEM_LENGTH
        )

        button = self.status_item.button()
        if button is not None:
            icon = NSImage.alloc().initByReferencingFile_(str(MENUBAR_ICON_PATH))
            icon.setScalesWhenResized_(True)
            icon.setSize_((STATUS_ICON_SIZE, STATUS_ICON_SIZE))
            icon.setTemplate_(True)

            button.setImage_(icon)
            button.setImagePosition_(NSImageLeft)
            button.setTitle_("")

        self.status_item.setMenu_(self._build_menu())

    def _build_menu(self):
        menu = NSMenu.alloc().init()

        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open Myorii", "openMyorii:", ""
        )
        open_item.setTarget_(self)
        menu.addItem_(open_item)

        status_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Myorii is running", None, ""
        )
        status_item.setEnabled_(False)
        menu.addItem_(status_item)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Myorii", "quitMyorii:", "q"
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        return menu

    def openMyorii_(self, sender) -> None:
        rumps.notification("Myorii", "Coming soon", "Main window will be connected next.")

    def quitMyorii_(self, sender) -> None:
        NSApplication.sharedApplication().terminate_(sender)


def run_menubar_app() -> None:
    """Run the macOS menu bar app."""

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = MyoriiMenuBarDelegate.alloc().init()
    app.setDelegate_(delegate)

    AppHelper.runEventLoop()
