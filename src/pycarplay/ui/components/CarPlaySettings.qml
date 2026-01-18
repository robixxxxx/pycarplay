// CarPlay Settings Panel Component
// This component can be customized or replaced with your own settings UI

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: settingsPanel
    anchors.fill: parent
    color: "#1e1e1e"
    visible: false
    z: 500
    
    property var videoController
    signal settingsApplied()
    signal settingsCancelled()
    
    // Load current settings when panel becomes visible
    onVisibleChanged: {
        if (visible && videoController) {
            loadCurrentSettings()
        }
    }
    
    function loadCurrentSettings() {
        var width = videoController.getVideoWidth()
        var height = videoController.getVideoHeight()
        var dpi = videoController.getVideoDpi()
        
        // Set resolution combo box
        var resolutionText = width + "x" + height
        var foundPreset = false
        
        for (var i = 0; i < resolutionCombo.model.length - 1; i++) {
            if (resolutionCombo.model[i] === resolutionText) {
                resolutionCombo.currentIndex = i
                foundPreset = true
                break
            }
        }
        
        if (!foundPreset) {
            resolutionCombo.currentIndex = resolutionCombo.model.length - 1
            widthField.text = width.toString()
            heightField.text = height.toString()
            customResolutionFields.visible = true
        } else {
            customResolutionFields.visible = false
        }
        
        dpiSpinBox.value = dpi
    }
    
    function applySettings() {
        var width, height
        
        if (customResolutionFields.visible) {
            width = parseInt(widthField.text)
            height = parseInt(heightField.text)
        } else {
            var resolution = resolutionCombo.currentText.split('x')
            width = parseInt(resolution[0])
            height = parseInt(resolution[1])
        }
        
        var dpi = dpiSpinBox.value
        
        if (isNaN(width) || isNaN(height) || width < 320 || height < 240) {
            console.log("Invalid resolution values")
            return
        }
        
        videoController.setVideoSettings(width, height, dpi)
        
        if (iconPathField.text !== "") {
            videoController.setCarPlayIcon(iconPathField.text)
        }
        
        if (iconLabelField.text !== "") {
            videoController.setCarPlayLabel(iconLabelField.text)
        }
        
        console.log("Settings applied: " + width + "x" + height + " @ " + dpi + " DPI")
        
        settingsApplied()
        visible = false
    }
    
    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        
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
            
            // Connection settings
            GroupBox {
                title: "🔌 Połączenie"
                Layout.fillWidth: true
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "Status:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        Rectangle {
                            Layout.preferredWidth: 180
                            Layout.preferredHeight: 30
                            color: videoController && videoController.dongleStatus.startsWith("Connected") ? "#28a745" : 
                                   videoController && (videoController.dongleStatus.startsWith("Connecting") || 
                                   videoController.dongleStatus.startsWith("Reconnecting")) ? "#ffc107" : 
                                   videoController && videoController.dongleStatus.startsWith("Failed") ? "#dc3545" : "#6c757d"
                            radius: 4
                            
                            Label {
                                anchors.centerIn: parent
                                text: videoController ? videoController.dongleStatus : "Not connected"
                                color: "#ffffff"
                                font.bold: true
                                font.pixelSize: 11
                            }
                        }
                        
                        Button {
                            text: videoController && videoController.dongleStatus.startsWith("Connected") ? "Rozłącz" : "Połącz"
                            Layout.preferredWidth: 120
                            enabled: videoController && 
                                    !videoController.dongleStatus.startsWith("Connecting") && 
                                    !videoController.dongleStatus.startsWith("Reconnecting")
                            onClicked: {
                                if (videoController.dongleStatus.startsWith("Connected")) {
                                    videoController.disconnectDongle()
                                } else {
                                    videoController.connectDongle()
                                }
                            }
                        }
                    }
                }
            }
            
            // Video settings
            GroupBox {
                title: "🖥️ Video Settings"
                Layout.fillWidth: true
                
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 15
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "Resolution:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        ComboBox {
                            id: resolutionCombo
                            Layout.preferredWidth: 150
                            model: [
                                "800x480",
                                "1024x600", 
                                "1280x720",
                                "1920x1080",
                                "Custom"
                            ]
                            currentIndex: 2
                            
                            onCurrentTextChanged: {
                                if (currentText === "Custom") {
                                    customResolutionFields.visible = true
                                } else if (currentText.includes('x')) {
                                    customResolutionFields.visible = false
                                    var res = currentText.split('x')
                                    widthField.text = res[0]
                                    heightField.text = res[1]
                                }
                            }
                        }
                        
                        RowLayout {
                            id: customResolutionFields
                            visible: false
                            spacing: 5
                            
                            TextField {
                                id: widthField
                                placeholderText: "Width"
                                text: "1280"
                                validator: IntValidator { bottom: 320; top: 3840 }
                                Layout.preferredWidth: 80
                            }
                            
                            Label {
                                text: "×"
                                color: "#ffffff"
                            }
                            
                            TextField {
                                id: heightField
                                placeholderText: "Height"
                                text: "720"
                                validator: IntValidator { bottom: 240; top: 2160 }
                                Layout.preferredWidth: 80
                            }
                        }
                    }
                    
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        
                        Label {
                            text: "DPI:"
                            color: "#ffffff"
                            Layout.preferredWidth: 180
                        }
                        
                        SpinBox {
                            id: dpiSpinBox
                            from: 72
                            to: 600
                            value: 160
                            stepSize: 10
                            Layout.fillWidth: true
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
                            Layout.fillWidth: true
                        }
                        
                        Button {
                            text: "Browse..."
                            onClicked: iconFileDialog.open()
                        }
                    }
                    
                    Label {
                        text: "Icon: PNG format, 256x256 pixels recommended"
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
                    onClicked: applySettings()
                }
                
                Button {
                    text: "Cancel"
                    font.pixelSize: 16
                    Layout.preferredWidth: 150
                    Layout.preferredHeight: 40
                    onClicked: {
                        settingsCancelled()
                        visible = false
                    }
                }
            }
            
            Label {
                text: "ℹ️ Settings will be auto-applied. Device will reload if phone is connected."
                color: "#888"
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                Layout.topMargin: 10
                horizontalAlignment: Text.AlignHCenter
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
            path = path.replace(/^(file:\/{2})/,"")
            path = decodeURIComponent(path)
            iconPathField.text = path
        }
    }
}
