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
    
    // Video Display
    VideoFrameProvider {
        id: videoDisplay
        objectName: "videoDisplay"
        anchors.fill: videoContainer
        fillMode: videoContainer.fillMode // "fit" or "stretch"
        // Touch/Mouse handling
        MouseArea {
            id: mouseArea
            anchors.fill: videoDisplay
            hoverEnabled: true
            
            property real pressX: 0
            property real pressY: 0
            property bool isDragging: false
            
            onPressed: (mouse) => {
                console.log("MouseArea.onPressed at", mouse.x, mouse.y)
                console.log("videoController present:", !!videoContainer.videoController)
                pressX = mouse.x
                pressY = mouse.y
                isDragging = false
                
                // Show touch indicator
                if (videoContainer.showTouchIndicator) {
                    touchIndicator.x = mouse.x - touchIndicator.width / 2
                    touchIndicator.y = mouse.y - touchIndicator.height / 2
                    touchIndicator.visible = true
                }
                
                if (videoContainer.videoController) {
                    try {
                        videoContainer.videoController.handleTouch(mouse.x, mouse.y, "down")
                        console.log("videoController.handleTouch invoked: down")
                    } catch (e) {
                        console.log("videoController.handleTouch error (down):", e)
                    }
                } else if (videoContainer.sendTouchFn) {
                    // Fallback: send normalized coords (0.0-1.0) via direct sendTouch slot
                    var nx = mouse.x / width
                    var ny = mouse.y / height
                    try {
                        // action code 14 = down
                        videoContainer.sendTouchFn(nx, ny, 14)
                        console.log("sendTouch invoked: down", nx, ny)
                    } catch (e) {
                        console.log("sendTouch error (down):", e)
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
                    
                    if (isDragging && videoContainer.showTouchIndicator) {
                        touchIndicator.x = mouse.x - touchIndicator.width / 2
                        touchIndicator.y = mouse.y - touchIndicator.height / 2
                    }
                    
                    if (videoContainer.videoController) {
                        try {
                            videoContainer.videoController.handleTouch(mouse.x, mouse.y, "move")
                            console.log("videoController.handleTouch invoked: move")
                        } catch (e) {
                            console.log("videoController.handleTouch error (move):", e)
                        }
                    } else if (videoContainer.sendTouchFn) {
                        var nxm = mouse.x / width
                        var nym = mouse.y / height
                        try {
                            // action code 15 = move
                            videoContainer.sendTouchFn(nxm, nym, 15)
                            console.log("sendTouch invoked: move", nxm, nym)
                        } catch (e) {
                            console.log("sendTouch error (move):", e)
                        }
                    } else {
                        console.log("videoController not available onPositionChanged")
                    }
                }
            }
            
            onReleased: (mouse) => {
                console.log("MouseArea.onReleased at", mouse.x, mouse.y)
                if (videoContainer.showTouchIndicator) {
                    touchIndicator.visible = false
                }
                
                if (videoContainer.videoController) {
                    try {
                        videoContainer.videoController.handleTouch(mouse.x, mouse.y, "up")
                        console.log("videoController.handleTouch invoked: up")
                    } catch (e) {
                        console.log("videoController.handleTouch error (up):", e)
                    }
                } else if (videoContainer.sendTouchFn) {
                    var nxu = mouse.x / width
                    var nyu = mouse.y / height
                    try {
                        // action code 16 = up
                        videoContainer.sendTouchFn(nxu, nyu, 16)
                        console.log("sendTouch invoked: up", nxu, nyu)
                    } catch (e) {
                        console.log("sendTouch error (up):", e)
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
