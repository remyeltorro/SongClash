"""Album cover downloads, with an in-memory and an on-disk cache."""

import os

from PyQt6 import sip
from PyQt6.QtCore import QObject, QStandardPaths, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkReply, QNetworkRequest

CACHE_SUBDIR = "ranksongs_images"  # kept from older versions so caches survive


class CoverLoader(QObject):
    """Loads cover images into QLabels asynchronously.

    Labels are often reused (the battle page) or destroyed (a closed
    leaderboard) before their download finishes; both cases are handled.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        disk_cache = QNetworkDiskCache(self)
        disk_cache.setCacheDirectory(
            os.path.join(
                QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation),
                CACHE_SUBDIR,
            )
        )
        self.network.setCache(disk_cache)
        self.network.finished.connect(self.on_reply_finished)
        self.pixmaps = {}  # url -> QPixmap
        self.active_downloads = {}  # QNetworkReply -> (url, label)

    def load(self, url, label):
        label.clear()
        # Remember which cover is wanted so late replies for a previous song
        # can't overwrite it
        label.setProperty("coverUrl", url or "")
        if not url:
            label.setText("No Cover")
            return
        if url in self.pixmaps:
            label.setPixmap(self.pixmaps[url])
            return
        label.setText("Loading...")
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(
            QNetworkRequest.Attribute.CacheLoadControlAttribute,
            QNetworkRequest.CacheLoadControl.PreferCache,
        )
        self.active_downloads[self.network.get(req)] = (url, label)

    def on_reply_finished(self, reply):
        url, label = self.active_downloads.pop(reply, (None, None))
        reply.deleteLater()
        pix = None
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pix = QPixmap()
            pix.loadFromData(reply.readAll())
            if pix.isNull():
                pix = None
            elif url:
                self.pixmaps[url] = pix
        # The label may belong to a window that was closed meanwhile
        if label is None or sip.isdeleted(label) or label.property("coverUrl") != url:
            return
        if pix:
            label.setPixmap(pix)
        else:
            label.setText("No Cover")
