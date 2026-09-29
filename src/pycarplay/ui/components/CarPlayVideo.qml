// CarPlay Video Display Component
// This is the core video display component that can be customized or replaced


import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import PyCarPlay 1.0

Rectangle {
    id: videoContainer
    color: "#1e1e1e"
    
    property var videoController
    property bool showTouchIndicator: true
    property bool showMediaInfo: true
    property bool showNavigationInfo: true
    property string fillMode: "fit"  // "fit" or "stretch"
    property var sendTouchFn: (typeof sendTouch === "function" ? sendTouch : null)
    property var activeTouches: []
    property bool multiTouchActive: false

    function forwardTouches(points, action) {
        var touchData = []
        var active = activeTouches.slice(0)
        for (var i = 0; i < points.length; ++i) {
            var point = points[i]
            var touchId = point.pointId
            var existingIndex = active.findIndex(function (touch) { return touch.id === touchId })
            if (action === "up") {
                if (existingIndex !== -1)
                    active.splice(existingIndex, 1)
            } else {
                var indicator = { id: touchId, x: point.x, y: point.y }
                if (existingIndex === -1)
                    active.push(indicator)
                else
                    active[existingIndex] = indicator
            }
            touchData.push({ x: point.x, y: point.y, id: touchId, action: action })
        }
        activeTouches = active

        if (active.length > 1)
            multiTouchActive = true

        if (multiTouchActive && videoController && typeof videoController.handleMultiTouch === "function") {
            videoController.handleMultiTouch(touchData)
        } else if (videoController && typeof videoController.handleTouch === "function") {
            for (var j = 0; j < touchData.length; ++j)
                videoController.handleTouch(touchData[j].x, touchData[j].y, action)
        } else if (sendTouchFn) {
            var actionCode = action === "down" ? 14 : action === "up" ? 16 : 15
            for (var k = 0; k < touchData.length; ++k)
                sendTouchFn(touchData[k].x / width, touchData[k].y / height, actionCode)
        }

        if (multiTouchActive && active.length === 0)
            multiTouchActive = false
    }
    
    // Video Display
    VideoFrameProvider {
        id: videoDisplay
        objectName: "videoDisplay"
        anchors.fill: videoContainer
        fillMode: videoContainer.fillMode // "fit" or "stretch"
        // Multi-touch input; mouse input is retained by MultiPointTouchArea.
        MultiPointTouchArea {
            id: multiTouchArea
            anchors.fill: videoDisplay
            maximumTouchPoints: 5
            mouseEnabled: true
            touchPoints: [
                TouchPoint {}, TouchPoint {}, TouchPoint {}, TouchPoint {}, TouchPoint {}
            ]

            onPressed: (points) => videoContainer.forwardTouches(points, "down")
            onUpdated: (points) => videoContainer.forwardTouches(points, "move")
            onReleased: (points) => videoContainer.forwardTouches(points, "up")
            onCanceled: (points) => videoContainer.forwardTouches(points, "up")
        }

        Repeater {
            model: videoContainer.showTouchIndicator ? videoContainer.activeTouches : []
            delegate: Rectangle {
                required property var modelData
                x: modelData.x - width / 2
                y: modelData.y - height / 2
                width: 40
                height: 40
                radius: 20
                color: "#4400aaff"
                border.color: "#0078d4"
                border.width: 2
                z: 100

                Rectangle {
                    anchors.centerIn: parent
                    width: 10
                    height: 10
                    radius: 5
                    color: "#0078d4"
                }
            }
        }
    }
    
    // Connection status overlay (when not connected)
    Rectangle {
        id: connectionOverlay
        anchors.fill: videoContainer
        color: "#1e1e1e"
        visible: !!videoContainer.videoController && typeof videoContainer.videoController.dongleStatus === "string" && !videoContainer.videoController.dongleStatus.startsWith("Connected")
        
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 20
            
            Label {
                text: videoContainer.videoController && typeof videoContainer.videoController.dongleStatus === "string" ? 
                      (videoContainer.videoController.dongleStatus.startsWith("Connecting") || 
                       videoContainer.videoController.dongleStatus.startsWith("Reconnecting") ?
                       "Łączenie z dongle..." : 
                       videoContainer.videoController.dongleStatus.startsWith("Failed") ?
                       "Błąd połączenia" :
                       (videoContainer.videoController.getWaitingConnectionText ? videoContainer.videoController.getWaitingConnectionText() : "Czekam na połączenie...")) :
                      (videoContainer.videoController && videoContainer.videoController.getWaitingConnectionText ? videoContainer.videoController.getWaitingConnectionText() : "Czekam na połączenie...")
                font.pixelSize: 18
                font.bold: true
                color: "#ffffff"
                Layout.alignment: Qt.AlignHCenter
            }
            
            Label {
                text: videoContainer.videoController && typeof videoContainer.videoController.dongleStatus === "string" ? videoContainer.videoController.dongleStatus : ""
                font.pixelSize: 12
                color: "#888"
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
    
    // Media Info Bar (Music & Navigation) - Overlay at bottom
    Rectangle {
        id: mediaInfoBar
        anchors.left: videoContainer.left
        anchors.right: videoContainer.right
        anchors.bottom: videoContainer.bottom
        height: 60
        color: "#aa2d2d2d"  // Semi-transparent
        visible: !!videoContainer.videoController && (
            (videoContainer.showMediaInfo && typeof videoContainer.videoController.currentSong === "string" && videoContainer.videoController.currentSong !== "") ||
            (videoContainer.showNavigationInfo && typeof videoContainer.videoController.navigationInfo === "string" && videoContainer.videoController.navigationInfo !== "")
        )

        RowLayout {
            anchors.fill: mediaInfoBar
            anchors.margins: 10
            spacing: 15

            // Music Info
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                visible: videoContainer.showMediaInfo && !!videoContainer.videoController && typeof videoContainer.videoController.currentSong === "string" && videoContainer.videoController.currentSong !== ""
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 2
                    
                    Label {
                        text: (videoContainer.videoController && typeof videoContainer.videoController.currentSong === "string" ? videoContainer.videoController.currentSong : "")
                        color: "#ffffff"
                        font.pixelSize: 14
                        font.bold: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    
                    Label {
                        text: (videoContainer.videoController && typeof videoContainer.videoController.currentArtist === "string" ? videoContainer.videoController.currentArtist : "")
                        color: "#aaa"
                        font.pixelSize: 12
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                }
            }
            
            // Separator
            Rectangle {
                Layout.preferredWidth: 1
                Layout.preferredHeight: 40
                color: "#444"
                visible: videoContainer.showMediaInfo && videoContainer.showNavigationInfo &&
                         !!videoContainer.videoController &&
                         typeof videoContainer.videoController.currentSong === "string" && videoContainer.videoController.currentSong !== "" &&
                         typeof videoContainer.videoController.navigationInfo === "string" && videoContainer.videoController.navigationInfo !== ""
            }
            
            // Navigation Info
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                visible: videoContainer.showNavigationInfo && !!videoContainer.videoController && typeof videoContainer.videoController.navigationInfo === "string" && videoContainer.videoController.navigationInfo !== ""
                
                Label {
                    anchors.fill: parent
                    text: "  " + (videoContainer.videoController && typeof videoContainer.videoController.navigationInfo === "string" ? videoContainer.videoController.navigationInfo : "")
                    color: "#4CAF50"
                    font.pixelSize: 14
                    font.bold: true
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }
}
