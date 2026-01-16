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
            }
        }
    }
}
