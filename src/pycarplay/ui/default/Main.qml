// Default PyCarPlay Main Window
// This file can be completely replaced by providing custom_qml_path in CarPlayConfig

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
Rectangle {
    id: mainWindow
    width: videoController ? videoController.getVideoWidth() : 1280
    height: videoController ? videoController.getVideoHeight() : 720
    color: "#1e1e1e"
    
    // Update window size when video config changes
    Connections {
        target: videoController
        function onVideoConfigChanged(width, height, dpi) {
            mainWindow.width = width
            mainWindow.height = height
            console.log("Window resized to: " + width + "x" + height)
        }
    }
    
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
    
    // Settings applied notification
    Rectangle {
        id: settingsAppliedNotification
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 20
        width: 400
        height: 60
        color: "#28a745"
        radius: 8
        visible: false
        z: 2000
        
        RowLayout {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 10
            
            Label {
                text: "[OK]"
                font.pixelSize: 18
                color: "#ffffff"
            }
            
            Label {
                text: "Settings applied! Device reloading..."
                font.pixelSize: 14
                font.bold: true
                color: "#ffffff"
                Layout.fillWidth: true
            }
        }
        
        Timer {
            id: settingsAppliedTimer
            interval: 3000
            onTriggered: settingsAppliedNotification.visible = false
        }
    }

    // Video Player Component
    CarPlayVideo {
        id: carplayVideo
        anchors.fill: parent
        videoController: mainWindow.videoController
        showTouchIndicator: true
        showMediaInfo: true
        showNavigationInfo: true
    }
    
    // Settings Panel Component
    CarPlaySettings {
        id: settingsPanel
        videoController: mainWindow.videoController
        
        onSettingsApplied: {
            settingsAppliedNotification.visible = true
            settingsAppliedTimer.start()
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
                text: " Keyboard Shortcuts"
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
                
                Label { text: "///"; color: "#0078d4"; font.bold: true }
                Label { text: "Navigate"; color: "#aaa" }
            }
            
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: "#444"
            }
            
            Label {
                text: " Mouse/Touch"
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
    
    // Connect signals from controller
    Connections {
        target: videoController
        
        function onShowConfigPanel() {
            settingsPanel.visible = true
        }
        
        function onHideConfigPanel() {
            settingsPanel.visible = false
        }
    }
}
