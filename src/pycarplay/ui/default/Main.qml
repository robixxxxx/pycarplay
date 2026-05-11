// Default PyCarPlay Main Window
// This file can be completely replaced by providing custom_qml_path in CarPlayConfig

import QtQuick
import QtQuick.Controls 2.15
import QtQuick.Layouts
import "../components"
Rectangle {
    id: mainWindow
    width: vc ? vc.getVideoWidth() : 1280
    height: vc ? vc.getVideoHeight() : 720
    color: "#1e1e1e"
    property var vc: videoController
    
    // Update window size when video config changes
    Connections {
        target: mainWindow.vc
        function onVideoConfigChanged(width, height, dpi) {
            mainWindow.width = width
            mainWindow.height = height
            console.log("Window resized to: " + width + "x" + height)
        }
    }
    
    // Keyboard shortcuts for CarPlay navigation
    Shortcut {
        sequence: "Escape"
        onActivated: if (mainWindow.vc) mainWindow.vc.sendKey("back")
    }
    
    Shortcut {
        sequence: "H"
        onActivated: if (mainWindow.vc) mainWindow.vc.sendKey("home")
    }
    
    Shortcut {
        sequence: "Space"
        onActivated: if (mainWindow.vc) mainWindow.vc.sendKey("playOrPause")
    }
    
    Shortcut {
        sequence: "Left"
        onActivated: if (mainWindow.vc) mainWindow.vc.sendKey("left")
    }
    
    Shortcut {
        sequence: "Right"
        onActivated: if (mainWindow.vc) mainWindow.vc.sendKey("right")
    }
    
    Shortcut {
        sequence: "Up"
        onActivated: if (mainWindow.vc) mainWindow.vc.sendKey("up")
    }
    
    Shortcut {
        sequence: "Down"
        onActivated: if (mainWindow.vc) mainWindow.vc.sendKey("down")
    }
    
    // Video Player Component
    CarPlayVideo {
        id: carplayVideo
        objectName: "carplayVideo"
        anchors.fill: mainWindow
        videoController: mainWindow.vc
        showTouchIndicator: true
        showMediaInfo: true
        showNavigationInfo: true
    }
    
    // Help Dialog
    Rectangle {
        id: helpDialog
        anchors.centerIn: mainWindow
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
                Layout.preferredHeight: 1
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
                Layout.preferredHeight: 1
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
    
}
