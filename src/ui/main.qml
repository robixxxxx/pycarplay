import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

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
        
        // Media Info Bar (Music & Navigation)
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: "#2d2d2d"
            radius: 8
            visible: videoController.currentSong !== "" || videoController.navigationInfo !== ""

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 15

                // Music Info
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    visible: videoController.currentSong !== ""
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 2
                        
                        Label {
                            text: "🎵 " + videoController.currentSong
                            color: "#ffffff"
                            font.pixelSize: 14
                            font.bold: true
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        
                        Label {
                            text: videoController.currentArtist
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
                    visible: videoController.currentSong !== "" && videoController.navigationInfo !== ""
                }
                
                // Navigation Info
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 40
                    visible: videoController.navigationInfo !== ""
                    
                    Label {
                        anchors.fill: parent
                        text: "🗺️  " + videoController.navigationInfo
                        color: "#4CAF50"
                        font.pixelSize: 14
                        font.bold: true
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

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
                
                // Media logging toggle button
                Button {
                    id: loggingButton
                    text: "📝"
                    font.pixelSize: 16
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 30
                    property bool loggingEnabled: false
                    ToolTip.visible: hovered
                    ToolTip.text: loggingEnabled ? "Stop media logging" : "Start media logging"
                    onClicked: {
                        if (loggingEnabled) {
                            videoController.stopMediaLogging()
                            loggingEnabled = false
                            text = "📝"
                        } else {
                            videoController.startMediaLogging()
                            loggingEnabled = true
                            text = "📝✅"
                        }
                    }
                }
                
                // Microphone button
                Button {
                    id: micButton
                    text: "🎤"
                    font.pixelSize: 16
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 30
                    property bool micEnabled: false
                    ToolTip.visible: hovered
                    ToolTip.text: micEnabled ? "Stop microphone" : "Start microphone (Siri/Calls)"
                    onClicked: {
                        if (micEnabled) {
                            videoController.stopMicrophone()
                            micEnabled = false
                            text = "🎤"
                        } else {
                            videoController.startMicrophone()
                            micEnabled = true
                            text = "🎤🔴"
                        }
                    }
                }
                
                // Audio toggle button
                Button {
                    id: audioButton
                    text: "🔊"
                    font.pixelSize: 16
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 30
                    property bool audioEnabled: true
                    ToolTip.visible: hovered
                    ToolTip.text: audioEnabled ? "Mute audio" : "Unmute audio"
                    onClicked: {
                        videoController.toggleAudio()
                        audioEnabled = !audioEnabled
                        text = audioEnabled ? "🔊" : "🔇"
                    }
                }
                
                // Help button
                Button {
                    text: "?"
                    font.bold: true
                    Layout.preferredWidth: 30
                    Layout.preferredHeight: 30
                    onClicked: helpDialog.visible = !helpDialog.visible
                    ToolTip.visible: hovered
                    ToolTip.text: "Keyboard shortcuts"
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
    
    // File dialog for icon selection
    FileDialog {
        id: iconFileDialog
        title: "Select CarPlay Icon"
        nameFilters: ["PNG images (*.png)", "All files (*)"]
        onAccepted: {
            var path = iconFileDialog.currentFile.toString()
            // Remove "file://" prefix
            path = path.replace(/^(file:\/{2})/,"")
            // Decode URI
            path = decodeURIComponent(path)
            iconPathField.text = path
        }
    }
    
    // CarPlay Config Panel (shown instead of video when command 1 received)
    Rectangle {
        id: configPanel
        anchors.fill: parent
        color: "#1e1e1e"
        visible: false
        z: 500
        
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 30
            width: 600
            
            Label {
                text: "⚙️ CarPlay Configuration"
                font.pixelSize: 32
                font.bold: true
                color: "#ffffff"
                Layout.alignment: Qt.AlignHCenter
            }
            
            // Microphone settings
            GroupBox {
                title: "🎤 Microphone Settings"
                Layout.fillWidth: true
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "Microphone Device:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        ComboBox {
                            id: micDeviceCombo
                            model: ["Default", "Built-in Microphone", "External Mic"]
                            Layout.fillWidth: true
                        }
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "Sample Rate:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        ComboBox {
                            id: sampleRateCombo
                            model: ["16000 Hz", "44100 Hz", "48000 Hz"]
                            currentIndex: 0
                            Layout.fillWidth: true
                        }
                    }
                    
                    CheckBox {
                        text: "Enable noise cancellation"
                        checked: true
                        Layout.fillWidth: true
                    }
                }
            }
            
            // Audio settings
            GroupBox {
                title: "🔊 Audio Settings"
                Layout.fillWidth: true
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "Output Device:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        ComboBox {
                            id: audioDeviceCombo
                            model: ["Default", "Built-in Speakers", "HDMI Output"]
                            Layout.fillWidth: true
                        }
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "Buffer Size:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        Slider {
                            from: 10
                            to: 40
                            value: 20
                            stepSize: 5
                            Layout.fillWidth: true
                            
                            Label {
                                anchors.right: parent.right
                                anchors.rightMargin: -60
                                anchors.verticalCenter: parent.verticalCenter
                                text: Math.round(parent.value) + "s"
                                color: "#ffffff"
                            }
                        }
                    }
                }
            }
            
            // CarPlay appearance settings
            GroupBox {
                title: "🚗 CarPlay Appearance"
                Layout.fillWidth: true
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "Icon Label:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        TextField {
                            id: iconLabelField
                            placeholderText: "PyCarPlay"
                            text: "PyCarPlay"
                            Layout.fillWidth: true
                        }
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "Icon Image:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        TextField {
                            id: iconPathField
                            placeholderText: "/path/to/icon.png"
                            text: "/Users/robertburda/dev/python/pycarplay/assets/icons/logo.png"
                            Layout.fillWidth: true
                        }
                        
                        Button {
                            text: "Browse..."
                            onClicked: {
                                iconFileDialog.open()
                            }
                        }
                    }
                    
                    Label {
                        text: "Icon should be PNG format, recommended size: 256x256 pixels"
                        color: "#888"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                    
                    Label {
                        text: "Label will appear on iPhone's CarPlay home screen"
                        color: "#888"
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }
            }
            
            // Action buttons
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 20
                
                Button {
                    text: "Apply Settings"
                    font.pixelSize: 16
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 40
                    onClicked: {
                        // Apply CarPlay icon if specified
                        if (iconPathField.text !== "") {
                            videoController.setCarPlayIcon(iconPathField.text)
                        }
                        
                        // Apply CarPlay label if changed
                        if (iconLabelField.text !== "") {
                            videoController.setCarPlayLabel(iconLabelField.text)
                        }
                        
                        console.log("Settings applied")
                        configPanel.visible = false
                    }
                }
                
                Button {
                    text: "Cancel"
                    font.pixelSize: 16
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 40
                    onClicked: {
                        configPanel.visible = false
                    }
                }
            }
        }
    }
    
    // Connect signals from controller
    Connections {
        target: videoController
        
        function onShowConfigPanel() {
            configPanel.visible = true
        }
        
        function onHideConfigPanel() {
            configPanel.visible = false
        }
    }
}
