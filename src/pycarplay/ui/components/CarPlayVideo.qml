// CarPlay Video Display Component
// This is the core video display component that can be customized or replaced

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

Rectangle {
    id: videoContainer
    color: "#1e1e1e"
    
    property var videoController
    property bool showTouchIndicator: true
    property bool showMediaInfo: true
    property bool showNavigationInfo: true
    property string fillMode: "fit"  // "fit" or "stretch"
    
    // Video Display
    VideoFrameProvider {
        id: videoDisplay
        anchors.fill: parent
        fillMode: videoContainer.fillMode // "fit" or "stretch"
        // Touch/Mouse handling
        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            
            property real pressX: 0
            property real pressY: 0
            property bool isDragging: false
            
            onPressed: (mouse) => {
                pressX = mouse.x
                pressY = mouse.y
                isDragging = false
                
                // Show touch indicator
                if (showTouchIndicator) {
                    touchIndicator.x = mouse.x - touchIndicator.width / 2
                    touchIndicator.y = mouse.y - touchIndicator.height / 2
                    touchIndicator.visible = true
                }
                
                if (videoController) {
                    videoController.handleTouch(mouse.x, mouse.y, "down")
                }
            }
            
            onPositionChanged: (mouse) => {
                if (pressed) {
                    var dx = Math.abs(mouse.x - pressX)
                    var dy = Math.abs(mouse.y - pressY)
                    
                    if (dx > 5 || dy > 5) {
                        isDragging = true
                    }
                    
                    if (isDragging && showTouchIndicator) {
                        touchIndicator.x = mouse.x - touchIndicator.width / 2
                        touchIndicator.y = mouse.y - touchIndicator.height / 2
                    }
                    
                    if (videoController) {
                        videoController.handleTouch(mouse.x, mouse.y, "move")
                    }
                }
            }
            
            onReleased: (mouse) => {
                if (showTouchIndicator) {
                    touchIndicator.visible = false
                }
                
                if (videoController) {
                    videoController.handleTouch(mouse.x, mouse.y, "up")
                }
            }
        }
        
        // Touch indicator
        Rectangle {
            id: touchIndicator
            width: 40
            height: 40
            radius: 20
            color: "#4400aaff"
            border.color: "#0078d4"
            border.width: 2
            visible: false
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
    
    // Connection status overlay (when not connected)
    Rectangle {
        anchors.fill: parent
        color: "#1e1e1e"
        visible: !!videoController && typeof videoController.dongleStatus === "string" && !videoController.dongleStatus.startsWith("Connected")
        
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 20
            
            Label {
                text: ""
                font.pixelSize: 64
                color: "#444"
                Layout.alignment: Qt.AlignHCenter
            }
            
            Label {
                text: videoController && typeof videoController.dongleStatus === "string" ? 
                      (videoController.dongleStatus.startsWith("Connecting") || 
                       videoController.dongleStatus.startsWith("Reconnecting") ?
                       "Łączenie z dongle..." : 
                       videoController.dongleStatus.startsWith("Failed") ?
                       "Błąd połączenia" :
                       "Czekam na połączenie...") :
                      "Czekam na połączenie..."
                font.pixelSize: 18
                font.bold: true
                color: "#ffffff"
                Layout.alignment: Qt.AlignHCenter
            }
            
            Label {
                text: videoController && typeof videoController.dongleStatus === "string" ? videoController.dongleStatus : ""
                font.pixelSize: 12
                color: "#888"
                Layout.alignment: Qt.AlignHCenter
            }
        }
    }
    
    // Media Info Bar (Music & Navigation) - Overlay at bottom
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 60
        color: "#aa2d2d2d"  // Semi-transparent
        visible: !!videoController && (
            (showMediaInfo && typeof videoController.currentSong === "string" && videoController.currentSong !== "") ||
            (showNavigationInfo && typeof videoController.navigationInfo === "string" && videoController.navigationInfo !== "")
        )

        RowLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 15

            // Music Info
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                visible: showMediaInfo && !!videoController && typeof videoController.currentSong === "string" && videoController.currentSong !== ""
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 2
                    
                    Label {
                        text: (videoController && typeof videoController.currentSong === "string" ? videoController.currentSong : "")
                        color: "#ffffff"
                        font.pixelSize: 14
                        font.bold: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }
                    
                    Label {
                        text: (videoController && typeof videoController.currentArtist === "string" ? videoController.currentArtist : "")
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
                visible: showMediaInfo && showNavigationInfo &&
                         !!videoController &&
                         typeof videoController.currentSong === "string" && videoController.currentSong !== "" &&
                         typeof videoController.navigationInfo === "string" && videoController.navigationInfo !== ""
            }
            
            // Navigation Info
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 40
                visible: showNavigationInfo && !!videoController && typeof videoController.navigationInfo === "string" && videoController.navigationInfo !== ""
                
                Label {
                    anchors.fill: parent
                    text: "  " + (videoController && typeof videoController.navigationInfo === "string" ? videoController.navigationInfo : "")
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
