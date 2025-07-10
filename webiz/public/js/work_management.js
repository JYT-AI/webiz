// Site Management JavaScript utilities
// Copyright (c) 2025, JYT AI and contributors

frappe.provide('webiz.site_management');
frappe.provide('webiz.work_management');

// Ensure webiz.work_management is properly initialized
if (typeof webiz === 'undefined') {
    window.webiz = {};
}
if (typeof webiz.work_management === 'undefined') {
    webiz.work_management = {};
}

// Offline support functionality
webiz.site_management.offline = {
    storage_key: 'webiz_offline_data',

    // Store data for offline use
    store_data: function(key, data) {
        try {
            let offline_data = this.get_offline_data();
            offline_data[key] = {
                data: data,
                timestamp: new Date().getTime(),
                synced: false
            };
            localStorage.setItem(this.storage_key, JSON.stringify(offline_data));
            return true;
        } catch (e) {
            console.error('Failed to store offline data:', e);
            return false;
        }
    },

    // Get offline data
    get_offline_data: function() {
        try {
            let data = localStorage.getItem(this.storage_key);
            return data ? JSON.parse(data) : {};
        } catch (e) {
            console.error('Failed to get offline data:', e);
            return {};
        }
    },

    // Get specific data by key
    get_data: function(key) {
        let offline_data = this.get_offline_data();
        return offline_data[key] ? offline_data[key].data : null;
    },

    // Check if online
    is_online: function() {
        return navigator.onLine;
    },

    // Sync offline data when online
    sync_data: function() {
        if (!this.is_online()) {
            frappe.show_alert({
                message: __('Cannot sync: No internet connection'),
                indicator: 'red'
            });
            return;
        }

        let offline_data = this.get_offline_data();
        let sync_promises = [];

        for (let key in offline_data) {
            if (!offline_data[key].synced) {
                sync_promises.push(this.sync_item(key, offline_data[key]));
            }
        }

        if (sync_promises.length === 0) {
            frappe.show_alert({
                message: __('No data to sync'),
                indicator: 'blue'
            });
            return;
        }

        Promise.all(sync_promises).then(() => {
            frappe.show_alert({
                message: __('Data synced successfully'),
                indicator: 'green'
            });
        }).catch((error) => {
            frappe.show_alert({
                message: __('Sync failed: ') + error.message,
                indicator: 'red'
            });
        });
    },

    // Sync individual item
    sync_item: function(key, item) {
        return new Promise((resolve, reject) => {
            // Determine sync method based on key type
            let method = '';
            let args = item.data;

            if (key.startsWith('checkin_')) {
                method = 'webiz.api.work_management.mobile_checkin';
            } else if (key.startsWith('checkout_')) {
                method = 'webiz.api.work_management.mobile_checkout';
            } else if (key.startsWith('checklist_')) {
                method = 'webiz.api.work_management.update_checklist_item';
            }

            if (!method) {
                resolve(); // Skip unknown types
                return;
            }

            frappe.call({
                method: method,
                args: args,
                callback: function(r) {
                    if (r.message && r.message.status === 'success') {
                        // Mark as synced
                        let offline_data = webiz.site_management.offline.get_offline_data();
                        offline_data[key].synced = true;
                        localStorage.setItem(webiz.site_management.offline.storage_key, JSON.stringify(offline_data));
                        resolve();
                    } else {
                        reject(new Error(r.message ? r.message.message : 'Sync failed'));
                    }
                },
                error: function(error) {
                    reject(error);
                }
            });
        });
    },

    // Clear synced data
    clear_synced_data: function() {
        let offline_data = this.get_offline_data();
        let cleaned_data = {};

        for (let key in offline_data) {
            if (!offline_data[key].synced) {
                cleaned_data[key] = offline_data[key];
            }
        }

        localStorage.setItem(this.storage_key, JSON.stringify(cleaned_data));
    }
};

// Offline storage helpers
webiz.site_management.store_offline_checkin = function(data) {
    let key = `checkin_${Date.now()}`;
    if (webiz.site_management.offline.store_data(key, data)) {
        frappe.msgprint({
            title: __('Offline Check-in'),
            message: __('Check-in stored offline. Will sync when connection is restored.'),
            indicator: 'blue'
        });
    } else {
        frappe.msgprint({
            title: __('Error'),
            message: __('Failed to store check-in offline'),
            indicator: 'red'
        });
    }
};

webiz.site_management.store_offline_checkout = function(data) {
    let key = `checkout_${Date.now()}`;
    if (webiz.site_management.offline.store_data(key, data)) {
        frappe.msgprint({
            title: __('Offline Check-out'),
            message: __('Check-out stored offline. Will sync when connection is restored.'),
            indicator: 'blue'
        });
    } else {
        frappe.msgprint({
            title: __('Error'),
            message: __('Failed to store check-out offline'),
            indicator: 'red'
        });
    }
};

webiz.site_management.store_offline_checklist_update = function(data) {
    let key = `checklist_${Date.now()}`;
    if (webiz.site_management.offline.store_data(key, data)) {
        frappe.show_alert({
            message: __('Checklist update stored offline'),
            indicator: 'blue'
        });
    }
};

// Mobile-optimized interface helpers
webiz.site_management.mobile_interface = {
    // Check if device is mobile
    is_mobile: function() {
        return window.innerWidth <= 768 || /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    },

    // Optimize dialog for mobile
    optimize_dialog: function(dialog) {
        if (this.is_mobile()) {
            dialog.$wrapper.addClass('mobile-optimized');

            // Add mobile-specific CSS
            if (!$('#mobile-dialog-css').length) {
                $('head').append(`
                    <style id="mobile-dialog-css">
                        .mobile-optimized .modal-dialog {
                            margin: 10px;
                            max-width: calc(100% - 20px);
                        }
                        .mobile-optimized .form-control {
                            font-size: 16px; /* Prevent zoom on iOS */
                        }
                        .mobile-optimized .btn {
                            padding: 12px 20px;
                            font-size: 16px;
                        }
                        .mobile-optimized .modal-body {
                            padding: 15px;
                        }
                    </style>
                `);
            }
        }
    },

    // Show connection status
    show_connection_status: function() {
        let status = webiz.site_management.offline.is_online() ? 'Online' : 'Offline';
        let indicator = webiz.site_management.offline.is_online() ? 'green' : 'orange';

        frappe.show_alert({
            message: __('Connection Status: ') + __(status),
            indicator: indicator
        });
    },

    // Vibrate on mobile (if supported)
    vibrate: function(pattern = [100]) {
        if (navigator.vibrate) {
            navigator.vibrate(pattern);
        }
    }
};

// QR Code scanner functionality
webiz.site_management.qr_checkin = function() {
    let dialog = new frappe.ui.Dialog({
        title: __('QR Code Check-in'),
        fields: [
            {
                fieldtype: 'Link',
                fieldname: 'worker',
                label: __('Worker'),
                options: 'Employee',
                reqd: 1
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'HTML',
                fieldname: 'qr_scanner',
                label: __('QR Code Scanner')
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Data',
                fieldname: 'qr_data',
                label: __('QR Code Data'),
                read_only: 1
            },
            {
                fieldtype: 'Data',
                fieldname: 'work_site',
                label: __('Work Site'),
                read_only: 1
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Attach Image',
                fieldname: 'photo',
                label: __('Check-in Photo')
            },
            {
                fieldtype: 'Text',
                fieldname: 'notes',
                label: __('Notes')
            }
        ],
        primary_action_label: __('Check In'),
        primary_action: function(values) {
            if (!values.qr_data) {
                frappe.msgprint(__('Please scan QR code first'));
                return;
            }

            try {
                let qr_data = JSON.parse(values.qr_data);
                let qr_type = qr_data.type || qr_data.t;
                if (qr_type !== 'work_site_checkin' && qr_type !== 'wsc') {
                    frappe.msgprint(__('Invalid QR code for check-in'));
                    return;
                }

                frappe.call({
                    method: 'webiz.api.work_management.qr_checkin',
                    args: {
                        worker: values.worker,
                        qr_data: values.qr_data,
                        photo: values.photo,
                        notes: values.notes
                    },
                    callback: function(r) {
                        if (r.message && r.message.status === 'success') {
                            frappe.msgprint({
                                title: __('Success'),
                                message: r.message.message,
                                indicator: 'green'
                            });
                            dialog.hide();
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message ? r.message.message : __('QR Check-in failed'),
                                indicator: 'red'
                            });
                        }
                    }
                });
            } catch (e) {
                frappe.msgprint(__('Invalid QR code format'));
            }
        }
    });

    // Initialize QR scanner when dialog is shown
    dialog.show();

    // Add QR scanner HTML
    let scanner_html = `
        <div id="qr-scanner-container">
            <video id="qr-video" width="100%" height="300" style="border: 1px solid #ccc;"></video>
            <div class="mt-2">
                <button class="btn btn-primary btn-sm" id="start-scan">${__('Start Scanning')}</button>
                <button class="btn btn-secondary btn-sm" id="stop-scan">${__('Stop Scanning')}</button>
            </div>
        </div>
    `;

    dialog.fields_dict.qr_scanner.$wrapper.html(scanner_html);

    // QR Scanner implementation (requires qr-scanner library)
    if (typeof QrScanner !== 'undefined') {
        const video = document.getElementById('qr-video');
        const qrScanner = new QrScanner(video, result => {
            dialog.set_value('qr_data', result);
            try {
                let qr_data = JSON.parse(result);
                let work_site = qr_data.work_site || qr_data.ws;
                if (work_site) {
                    dialog.set_value('work_site', work_site);
                }
            } catch (e) {
                // Invalid JSON, but still set the raw data
            }
            qrScanner.stop();
        });

        $('#start-scan').click(function() {
            qrScanner.start();
        });

        $('#stop-scan').click(function() {
            qrScanner.stop();
        });
    } else {
        dialog.fields_dict.qr_scanner.$wrapper.html(`
            <div class="alert alert-warning">
                ${__('QR Scanner library not loaded. Please scan QR code manually and enter data below.')}
            </div>
            <input type="text" class="form-control" placeholder="${__('Enter QR code data manually')}"
                   onchange="cur_dialog.set_value('qr_data', this.value)">
        `);
    }
};

// Mobile check-in functionality with offline support
webiz.site_management.mobile_checkin = function() {
    let dialog = new frappe.ui.Dialog({
        title: __('Worker Check-in'),
        fields: [
            {
                fieldtype: 'Link',
                fieldname: 'worker',
                label: __('Worker'),
                options: 'Employee',
                reqd: 1
            },
            {
                fieldtype: 'Link',
                fieldname: 'work_site',
                label: __('Work Site'),
                options: 'Work Site',
                reqd: 1
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Button',
                fieldname: 'get_location',
                label: __('Get Current Location'),
                click: function() {
                    webiz.work_management.get_current_location(dialog);
                }
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Float',
                fieldname: 'latitude',
                label: __('Latitude'),
                precision: 8,
                read_only: 1
            },
            {
                fieldtype: 'Float',
                fieldname: 'longitude',
                label: __('Longitude'),
                precision: 8,
                read_only: 1
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Attach Image',
                fieldname: 'photo',
                label: __('Check-in Photo')
            },
            {
                fieldtype: 'Text',
                fieldname: 'notes',
                label: __('Notes')
            }
        ],
        primary_action_label: __('Check In'),
        primary_action: function(values) {
            let checkin_data = {
                worker: values.worker,
                work_site: values.work_site,
                latitude: values.latitude,
                longitude: values.longitude,
                photo: values.photo,
                notes: values.notes
            };

            // Try online first, fallback to offline
            if (webiz.site_management.offline.is_online()) {
                frappe.call({
                    method: 'webiz.api.work_management.mobile_checkin',
                    args: checkin_data,
                    callback: function(r) {
                        if (r.message && r.message.status === 'success') {
                            frappe.msgprint({
                                title: __('Success'),
                                message: r.message.message,
                                indicator: 'green'
                            });
                            dialog.hide();
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message ? r.message.message : __('Check-in failed'),
                                indicator: 'red'
                            });
                        }
                    },
                    error: function() {
                        // Store offline if API call fails
                        webiz.site_management.store_offline_checkin(checkin_data);
                        dialog.hide();
                    }
                });
            } else {
                // Store offline
                webiz.site_management.store_offline_checkin(checkin_data);
                dialog.hide();
            }
        }
    });
    
    dialog.show();
};

// Mobile check-out functionality with offline support
webiz.site_management.mobile_checkout = function() {
    let dialog = new frappe.ui.Dialog({
        title: __('Worker Check-out'),
        fields: [
            {
                fieldtype: 'Link',
                fieldname: 'worker',
                label: __('Worker'),
                options: 'Employee',
                reqd: 1
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Button',
                fieldname: 'get_location',
                label: __('Get Current Location'),
                click: function() {
                    webiz.work_management.get_current_location(dialog);
                }
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Float',
                fieldname: 'latitude',
                label: __('Latitude'),
                precision: 8,
                read_only: 1
            },
            {
                fieldtype: 'Float',
                fieldname: 'longitude',
                label: __('Longitude'),
                precision: 8,
                read_only: 1
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Attach Image',
                fieldname: 'photo',
                label: __('Check-out Photo')
            },
            {
                fieldtype: 'Text',
                fieldname: 'notes',
                label: __('Notes')
            }
        ],
        primary_action_label: __('Check Out'),
        primary_action: function(values) {
            let checkout_data = {
                worker: values.worker,
                latitude: values.latitude,
                longitude: values.longitude,
                photo: values.photo,
                notes: values.notes
            };

            // Try online first, fallback to offline
            if (webiz.site_management.offline.is_online()) {
                frappe.call({
                    method: 'webiz.api.work_management.mobile_checkout',
                    args: checkout_data,
                    callback: function(r) {
                        if (r.message && r.message.status === 'success') {
                            frappe.msgprint({
                                title: __('Success'),
                                message: r.message.message +
                                        (r.message.work_hours ? ` (${r.message.work_hours} hours worked)` : ''),
                                indicator: 'green'
                            });
                            dialog.hide();
                        } else {
                            frappe.msgprint({
                                title: __('Error'),
                                message: r.message ? r.message.message : __('Check-out failed'),
                                indicator: 'red'
                            });
                        }
                    },
                    error: function() {
                        // Store offline if API call fails
                        webiz.site_management.store_offline_checkout(checkout_data);
                        dialog.hide();
                    }
                });
            } else {
                // Store offline
                webiz.site_management.store_offline_checkout(checkout_data);
                dialog.hide();
            }
        }
    });
    
    dialog.show();

    // Optimize for mobile
    webiz.site_management.mobile_interface.optimize_dialog(dialog);
};

// Get current location using browser geolocation
webiz.work_management.get_current_location = function(dialog) {
    if (navigator.geolocation) {
        frappe.show_alert({
            message: __('Getting location...'),
            indicator: 'blue'
        });
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                dialog.set_value('latitude', position.coords.latitude);
                dialog.set_value('longitude', position.coords.longitude);
                frappe.show_alert({
                    message: __('Location obtained successfully'),
                    indicator: 'green'
                });
            },
            function(error) {
                let message = __('Unable to get location');
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        message = __('Location access denied by user');
                        break;
                    case error.POSITION_UNAVAILABLE:
                        message = __('Location information unavailable');
                        break;
                    case error.TIMEOUT:
                        message = __('Location request timed out');
                        break;
                }
                frappe.msgprint({
                    title: __('Location Error'),
                    message: message,
                    indicator: 'red'
                });
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    } else {
        frappe.msgprint({
            title: __('Not Supported'),
            message: __('Geolocation is not supported by this browser'),
            indicator: 'red'
        });
    }
};

// Quick checklist creation
webiz.site_management.create_quick_checklist = function() {
    let dialog = new frappe.ui.Dialog({
        title: __('Create Quick Checklist'),
        fields: [
            {
                fieldtype: 'Data',
                fieldname: 'checklist_name',
                label: __('Checklist Name'),
                reqd: 1
            },
            {
                fieldtype: 'Link',
                fieldname: 'work_site',
                label: __('Work Site'),
                options: 'Work Site',
                reqd: 1
            },
            {
                fieldtype: 'Link',
                fieldname: 'assigned_to',
                label: __('Assigned To'),
                options: 'Employee',
                reqd: 1
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'Table',
                fieldname: 'items',
                label: __('Checklist Items'),
                fields: [
                    {
                        fieldtype: 'Data',
                        fieldname: 'name',
                        label: __('Item Name'),
                        in_list_view: 1,
                        reqd: 1
                    },
                    {
                        fieldtype: 'Text',
                        fieldname: 'description',
                        label: __('Description'),
                        in_list_view: 1
                    },
                    {
                        fieldtype: 'Select',
                        fieldname: 'type',
                        label: __('Type'),
                        options: 'Task\nSafety Check\nQuality Check\nInspection\nMaintenance\nCleaning\nDocumentation',
                        default: 'Task',
                        in_list_view: 1
                    },
                    {
                        fieldtype: 'Check',
                        fieldname: 'mandatory',
                        label: __('Mandatory'),
                        in_list_view: 1
                    },
                    {
                        fieldtype: 'Float',
                        fieldname: 'max_score',
                        label: __('Max Score'),
                        default: 10,
                        in_list_view: 1
                    }
                ]
            }
        ],
        primary_action_label: __('Create Checklist'),
        primary_action: function(values) {
            if (!values.items || values.items.length === 0) {
                frappe.msgprint(__('Please add at least one checklist item'));
                return;
            }
            
            frappe.call({
                method: 'webiz.api.work_management.create_quick_checklist',
                args: {
                    work_site: values.work_site,
                    checklist_name: values.checklist_name,
                    assigned_to: values.assigned_to,
                    items_json: JSON.stringify(values.items)
                },
                callback: function(r) {
                    if (r.message && r.message.status === 'success') {
                        frappe.msgprint({
                            title: __('Success'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                        dialog.hide();
                        frappe.set_route('Form', 'Work Checklist', r.message.checklist_id);
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message ? r.message.message : __('Failed to create checklist'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    });
    
    // Add default items
    dialog.fields_dict.items.df.data = [
        {
            name: 'Safety Equipment Check',
            description: 'Verify all safety equipment is available and functional',
            type: 'Safety Check',
            mandatory: 1,
            max_score: 10
        },
        {
            name: 'Work Area Preparation',
            description: 'Prepare work area and organize tools',
            type: 'Task',
            mandatory: 1,
            max_score: 10
        },
        {
            name: 'Quality Inspection',
            description: 'Perform quality check on completed work',
            type: 'Quality Check',
            mandatory: 1,
            max_score: 15
        }
    ];
    
    dialog.show();
    dialog.fields_dict.items.grid.refresh();
};

// Work site dashboard
webiz.site_management.show_site_dashboard = function(work_site) {
    frappe.call({
        method: 'webiz.api.work_management.get_work_site_dashboard',
        args: { work_site: work_site },
        callback: function(r) {
            if (r.message) {
                let data = r.message;
                let html = `
                    <div class="work-site-dashboard">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h5>${__('Site Information')}</h5>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>${__('Site Name')}:</strong> ${data.site_info.site_name}</p>
                                        <p><strong>${__('Customer')}:</strong> ${data.site_info.customer}</p>
                                        <p><strong>${__('Status')}:</strong> <span class="badge badge-${data.site_info.status === 'Active' ? 'success' : 'secondary'}">${data.site_info.status}</span></p>
                                        <p><strong>${__('Manager')}:</strong> ${data.site_info.site_manager || 'Not assigned'}</p>
                                        <p><strong>${__('Location')}:</strong> ${data.site_info.location}</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h5>${__('Today\'s Attendance')}</h5>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>${__('Total Check-ins')}:</strong> ${data.attendance.total_checkins}</p>
                                        <p><strong>${__('Currently Present')}:</strong> ${data.attendance.currently_present}</p>
                                        <p><strong>${__('Total Work Hours')}:</strong> ${data.attendance.total_work_hours}</p>
                                        <p><strong>${__('Overtime Hours')}:</strong> ${data.attendance.total_overtime}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h5>${__('Checklists')}</h5>
                                    </div>
                                    <div class="card-body">
                                        <p><strong>${__('Pending')}:</strong> ${data.checklists.pending}</p>
                                        <p><strong>${__('Completed Today')}:</strong> ${data.checklists.completed_today}</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-header">
                                        <h5>${__('Recent Reports')}</h5>
                                    </div>
                                    <div class="card-body">
                                        ${data.recent_reports.map(report => 
                                            `<p><a href="/app/work-report/${report.name}">${report.report_title}</a> (${report.report_date})</p>`
                                        ).join('')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                frappe.msgprint({
                    title: __('Work Site Dashboard'),
                    message: html,
                    wide: true
                });
            }
        }
    });
};

// Add custom buttons to workspace
$(document).ready(function() {
    // Add buttons to site management workspace
    if (frappe.get_route()[0] === 'workspace' && frappe.get_route()[1] === '현장관리') {
        setTimeout(function() {
            if ($('.workspace-sidebar').length && !$('.custom-site-buttons').length) {
                let connection_status = webiz.site_management.offline.is_online() ? 'Online' : 'Offline';
                let connection_class = webiz.site_management.offline.is_online() ? 'success' : 'warning';

                let buttons_html = `
                    <div class="custom-site-buttons mt-3">
                        <div class="alert alert-${connection_class} text-center mb-2" style="padding: 5px;">
                            <small><i class="fa fa-wifi"></i> ${__(connection_status)}</small>
                        </div>
                        <button class="btn btn-primary btn-sm btn-block mb-2" onclick="webiz.site_management.mobile_checkin()">
                            <i class="fa fa-sign-in"></i> ${__('Quick Check-in')}
                        </button>
                        <button class="btn btn-success btn-sm btn-block mb-2" onclick="webiz.site_management.mobile_checkout()">
                            <i class="fa fa-sign-out"></i> ${__('Quick Check-out')}
                        </button>
                        <button class="btn btn-warning btn-sm btn-block mb-2" onclick="webiz.site_management.qr_checkin()">
                            <i class="fa fa-qrcode"></i> ${__('QR Check-in')}
                        </button>
                        <button class="btn btn-info btn-sm btn-block mb-2" onclick="webiz.site_management.create_quick_checklist()">
                            <i class="fa fa-list"></i> ${__('Quick Checklist')}
                        </button>
                        <button class="btn btn-secondary btn-sm btn-block mb-2" onclick="webiz.site_management.offline.sync_data()">
                            <i class="fa fa-sync"></i> ${__('Sync Offline Data')}
                        </button>
                        <button class="btn btn-light btn-sm btn-block mb-2" onclick="webiz.site_management.mobile_interface.show_connection_status()">
                            <i class="fa fa-info-circle"></i> ${__('Connection Status')}
                        </button>
                    </div>
                `;
                $('.workspace-sidebar').append(buttons_html);

                // Update connection status every 30 seconds
                setInterval(function() {
                    let new_status = webiz.site_management.offline.is_online() ? 'Online' : 'Offline';
                    let new_class = webiz.site_management.offline.is_online() ? 'success' : 'warning';
                    $('.custom-site-buttons .alert').removeClass('alert-success alert-warning').addClass(`alert-${new_class}`);
                    $('.custom-site-buttons .alert small').html(`<i class="fa fa-wifi"></i> ${__(new_status)}`);
                }, 30000);
            }
        }, 1000);
    }

    // Auto-sync when coming back online
    window.addEventListener('online', function() {
        frappe.show_alert({
            message: __('Connection restored. Syncing offline data...'),
            indicator: 'green'
        });
        setTimeout(function() {
            webiz.site_management.offline.sync_data();
        }, 2000);
    });

    // Show offline notification
    window.addEventListener('offline', function() {
        frappe.show_alert({
            message: __('Connection lost. Working in offline mode.'),
            indicator: 'orange'
        });
    });
});
