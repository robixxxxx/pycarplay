import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 1280
    height: 720
    title: "PyCarPlay - Video Stream"
    color: "#1e1e1e"
    
    // Keyboard shortcuts for CarPlay navigation
    Shortcut {
        sequence: "Escape"
        onActivated: videoController.sendKey("back")
    }
    
    Shortcut {
        sequence: "H"
        onActivated: videoController.sendKey("home")
    }
    
    Shortcut {
        sequence: "Space"
        onActivated: videoController.sendKey("playOrPause")
    }
    
    Shortcut {
        sequence: "Left"
        onActivated: videoController.sendKey("left")
    }
    
    Shortcut {
        sequence: "Right"
        onActivated: videoController.sendKey("right")
    }
    
    Shortcut {
        sequence: "Up"
        onActivated: videoController.sendKey("up")
    }
    
    Shortcut {
        sequence: "Down"
        onActivated: videoController.sendKey("down")
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10

        // Header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "#2d2d2d"
            radius: 8

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                Label {
                    text: "PyCarPlay Video Stream"
                    font.pixelSize: 24
                    font.bold: true
                    color: "#ffffff"
                    Layout.fillWidth: true
                }

                // Dongle status indicator
                Rectangle {
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 40
                    color: videoController.dongleStatus === "Connected" ? "#28a745" : 
                           videoController.dongleStatus === "Connecting..." ? "#ffc107" : "#dc3545"
                    radius: 4
                    
                    Label {
                        anchors.centerIn: parent
                        text: videoController.dongleStatus
                        color: "#ffffff"
                        font.bold: true
                    }
                }

                Button {
                    text: videoController.dongleStatus.startsWith("Connected") ? "Disconnect" : "Connect USB"
                    onClicked: {
                        if (videoController.dongleStatus.startsWith("Connected")) {
                            videoController.disconnectDongle()
                        } else {
                            videoController.connectDongle()
                        }
                    }
                    Layout.preferredWidth: 120
                }
            }
        }

        // Video Player Area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#000000"
            radius: 8
            border.color: "#3d3d3d"
            border.width: 2

            // Video display container - videoDisplay will be added from Python
            Item {
                id: videoContainer
                objectName: "videoContainer"
                anchors.fill: parent
                anchors.margins: 2
                
                // Touch handling
                MouseArea {
                    id: touchArea
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    
                    onPressed: function(mouse) {
                        // Convert screen coordinates to video coordinates (1280x720)
                        var videoCoords = videoDisplay.mapToVideoCoordinates(mouse.x, mouse.y)
                        if (videoCoords[0] >= 0 && videoCoords[1] >= 0) {
                            // TouchAction.Down = 14
                            videoController.sendTouch(videoCoords[0], videoCoords[1], 14)
                            // Show visual feedback at screen position
                            touchIndicator.x = mouse.x - touchIndicator.width / 2
                            touchIndicator.y = mouse.y - touchIndicator.height / 2
                            touchIndicator.visible = true
                        }
                    }
                    
                    onReleased: function(mouse) {
                        // Convert screen coordinates to video coordinates
                        var videoCoords = videoDisplay.mapToVideoCoordinates(mouse.x, mouse.y)
                        if (videoCoords[0] >= 0 && videoCoords[1] >= 0) {
                            // TouchAction.Up = 16
                            videoController.sendTouch(videoCoords[0], videoCoords[1], 16)
                        }
                        // Hide visual feedback
                        touchIndicator.visible = false
                    }
                    
                    onPositionChanged: function(mouse) {
                        if (pressed) {
                            // Convert screen coordinates to video coordinates
                            var videoCoords = videoDisplay.mapToVideoCoordinates(mouse.x, mouse.y)
                            if (videoCoords[0] >= 0 && videoCoords[1] >= 0) {
                                // TouchAction.Move = 15
                                videoController.sendTouch(videoCoords[0], videoCoords[1], 15)
                                // Update visual feedback position at screen position
                                touchIndicator.x = mouse.x - touchIndicator.width / 2
                                touchIndicator.y = mouse.y - touchIndicator.height / 2
                            }
                        }
                    }
                }
                
                // Touch indicator (visual feedback)
                Rectangle {
                    id: touchIndicator
                    width: 30
                    height: 30
                    radius: 15
                    color: "#4080ff80"
                    border.color: "#80ffffff"
                    border.width: 2
                    visible: false
                    z: 1000
                }
            }
            
            // Overlay items
            Item {
                anchors.fill: parent
                
                // Placeholder when no video
                Rectangle {
                    anchors.centerIn: parent
                    width: 400
                    height: 200
                    color: "#2d2d2d"
                    radius: 8
                    visible: videoDisplay.frameCount === 0
                    
                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 10
                        
                        Label {
                            text: "📹"
                            font.pixelSize: 64
                            color: "#888"
                            Layout.alignment: Qt.AlignHCenter
                        }
                        
                        Label {
                            text: "Czekam na wideo z CarPlay..."
                            font.pixelSize: 18
                            color: "#aaa"
                            Layout.alignment: Qt.AlignHCenter
                        }
                        
                        Label {
                            text: "Podłącz iPhone/Android do dongla"
                            font.pixelSize: 14
                            color: "#888"
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }
                
                // Frame counter overlay
                Rectangle {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 10
                    width: frameLabel.width + 20
                    height: frameLabel.height + 10
                    color: "#000000"
                    opacity: 0.7
                    radius: 4
                    visible: videoDisplay.frameCount > 0
                    
                    Label {
                        id: frameLabel
                        anchors.centerIn: parent
                        text: "Frame #" + videoDisplay.frameCount
                        color: "#00ff00"
                        font.family: "monospace"
                        font.pixelSize: 12
                    }
                }
            }
        }  // End of Video Player Area Rectangle

        // Info Bar
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: "#2d2d2d"
            radius: 8

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 20

                Label {
                    text: "📊 Status:"
                    color: "#aaa"
                    font.pixelSize: 14
                }

                Label {
                    id: statusLabel
                    text: videoDisplay.frameCount > 0 ? "Streaming active" : "Waiting for connection"
                    color: videoDisplay.frameCount > 0 ? "#00ff00" : "#888"
                    font.pixelSize: 14
                    font.bold: true
                }

                Label {
                    text: "•"
                    color: "#444"
                    font.pixelSize: 14
                }

                Label {
                    text: "Frames: " + videoDisplay.frameCount
                    color: "#aaa"
                    font.pixelSize: 14
                }

                Item { Layout.fillWidth: true }

                Label {
                    text: "PyCarPlay v1.0"
                    color: "#666"
                    font.pixelSize: 12
                }
                
                // Help button
                Button {
                    text: "?"
                    font.bold: true
                    Layout.preferredWidth: 30
                    Layout.preferredHeight: 30
                    onClicked: helpDialog.visible = !helpDialog.visible
                }
            }
        }
    }
    
    // Help Dialog
    Rectangle {
        id: helpDialog
        anchors.centerIn: parent
        width: 400
        height: 350
        color: "#2d2d2d"
        border.color: "#0078d4"
        border.width: 2
        radius: 8
        visible: false
        z: 1000
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 10
            
            Label {
                text: "⌨️ Keyboard Shortcuts"
                font.pixelSize: 18
                font.bold: true
                color: "#ffffff"
                Layout.alignment: Qt.AlignHCenter
            }
            
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#444"
            }
            
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 20
                
                Label { text: "ESC"; color: "#0078d4"; font.bold: true }
                Label { text: "Back"; color: "#aaa" }
                
                Label { text: "H"; color: "#0078d4"; font.bold: true }
                Label { text: "Home"; color: "#aaa" }
                
                Label { text: "SPACE"; color: "#0078d4"; font.bold: true }
                Label { text: "Play/Pause"; color: "#aaa" }
                
                Label { text: "←/→/↑/↓"; color: "#0078d4"; font.bold: true }
                Label { text: "Navigate"; color: "#aaa" }
            }
            
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#444"
            }
            
            Label {
                text: "🖱️ Mouse/Touch"
                font.pixelSize: 16
                font.bold: true
                color: "#ffffff"
                Layout.topMargin: 10
            }
            
            Label {
                text: "• Click and drag on video to interact with CarPlay"
                color: "#aaa"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            
            Label {
                text: "• Blue circle shows touch position"
                color: "#aaa"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
            
            Item { Layout.fillHeight: true }
            
            Button {
                text: "Close"
                Layout.alignment: Qt.AlignHCenter
                onClicked: helpDialog.visible = false
            }
        }
    }
}
