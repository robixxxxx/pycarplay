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
    
    // Video Display
    VideoFrameProvider {
        id: videoDisplay
        objectName: "videoDisplay"
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
                console.log("MouseArea.onPressed at", mouse.x, mouse.y)
                console.log("videoController present:", !!videoController)
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
                    try {
                        videoController.handleTouch(mouse.x, mouse.y, "down")
                        console.log("videoController.handleTouch invoked: down")
                    } catch (e) {
                        console.log("videoController.handleTouch error (down):", e)
                    }
                } else if (typeof sendTouchNormalized === 'function') {
                    // Fallback: send normalized coords (0.0-1.0)
                    var nx = mouse.x / width
                    var ny = mouse.y / height
                    try {
                        sendTouchNormalized(nx, ny, "down")
                        console.log("sendTouchNormalized invoked: down", nx, ny)
                    } catch (e) {
                        console.log("sendTouchNormalized error (down):", e)
                    }
                } else {
                    console.log("videoController not available onPressed")
                }
            }
            
            onPositionChanged: (mouse) => {
                if (pressed) console.log("MouseArea.onPositionChanged at", mouse.x, mouse.y)
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
                        try {
                            videoController.handleTouch(mouse.x, mouse.y, "move")
                            console.log("videoController.handleTouch invoked: move")
                        } catch (e) {
                            console.log("videoController.handleTouch error (move):", e)
                        }
                    } else if (typeof sendTouchNormalized === 'function') {
                        var nxm = mouse.x / width
                        var nym = mouse.y / height
                        try {
                            sendTouchNormalized(nxm, nym, "move")
                            console.log("sendTouchNormalized invoked: move", nxm, nym)
                        } catch (e) {
                            console.log("sendTouchNormalized error (move):", e)
                        }
                    } else {
                        console.log("videoController not available onPositionChanged")
                    }
                }
            }
            
            onReleased: (mouse) => {
                console.log("MouseArea.onReleased at", mouse.x, mouse.y)
                if (showTouchIndicator) {
                    touchIndicator.visible = false
                }
                
                if (videoController) {
                    try {
                        videoController.handleTouch(mouse.x, mouse.y, "up")
                        console.log("videoController.handleTouch invoked: up")
                    } catch (e) {
                        console.log("videoController.handleTouch error (up):", e)
                    }
                } else if (typeof sendTouchNormalized === 'function') {
                    var nxu = mouse.x / width
                    var nyu = mouse.y / height
                    try {
                        sendTouchNormalized(nxu, nyu, "up")
                        console.log("sendTouchNormalized invoked: up", nxu, nyu)
                    } catch (e) {
                        console.log("sendTouchNormalized error (up):", e)
                    }
                } else {
                    console.log("videoController not available onReleased")
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
