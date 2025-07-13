# Copyright (c) 2025, JYT AI and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import math


class WorkAttendance(Document):
	def validate(self):
		"""Validate Work Attendance data"""
		self.validate_times()
		self.validate_location()
	
	def validate_times(self):
		"""Validate time fields"""
		if self.in_time and self.out_time:
			if self.in_time >= self.out_time:
				frappe.throw("체크인 시간은 체크아웃 시간보다 이전이어야 합니다.")
	
	def validate_location(self):
		"""Validate location data"""
		if self.work_site and self.check_in_location:
			self.verify_location()
	
	def before_save(self):
		"""Before save operations"""
		self.calculate_working_hours()
		self.calculate_attendance_score()
		self.sync_with_attendance()
	
	def calculate_working_hours(self):
		"""Calculate working hours and overtime"""
		if self.in_time and self.out_time:
			in_time = datetime.strptime(str(self.in_time), "%Y-%m-%d %H:%M:%S")
			out_time = datetime.strptime(str(self.out_time), "%Y-%m-%d %H:%M:%S")
			
			total_hours = (out_time - in_time).total_seconds() / 3600
			self.total_working_hours = total_hours - (self.break_hours or 0)
			
			# Calculate overtime (assuming 8 hours standard)
			standard_hours = 8
			if self.total_working_hours > standard_hours:
				self.overtime_hours = self.total_working_hours - standard_hours
			else:
				self.overtime_hours = 0
	
	def verify_location(self):
		"""Verify location against work site"""
		if not self.work_site or not self.check_in_location:
			return
		
		# Get work site coordinates
		site_doc = frappe.get_doc("Customer Site", self.work_site)
		if not site_doc.latitude or not site_doc.longitude:
			return
		
		# Parse check-in location
		try:
			check_in_coords = self.check_in_location.split(',')
			check_in_lat = float(check_in_coords[0])
			check_in_lng = float(check_in_coords[1])
		except:
			return
		
		# Calculate distance
		distance = self.calculate_distance(
			float(site_doc.latitude), float(site_doc.longitude),
			check_in_lat, check_in_lng
		)
		
		self.distance_from_site = distance
		
		# Verify location (within 100 meters)
		if distance <= 100:
			self.location_verified = 1
		else:
			self.location_verified = 0
			frappe.msgprint(f"체크인 위치가 현장에서 {distance:.0f}m 떨어져 있습니다.")
	
	def calculate_distance(self, lat1, lon1, lat2, lon2):
		"""Calculate distance between two GPS coordinates in meters"""
		# Haversine formula
		R = 6371000  # Earth's radius in meters
		
		lat1_rad = math.radians(lat1)
		lat2_rad = math.radians(lat2)
		delta_lat = math.radians(lat2 - lat1)
		delta_lon = math.radians(lon2 - lon1)
		
		a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
			 math.cos(lat1_rad) * math.cos(lat2_rad) *
			 math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
		
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
		distance = R * c
		
		return distance
	
	def calculate_attendance_score(self):
		"""Calculate attendance score based on various factors"""
		score = 100
		
		# Deduct points for location verification failure
		if not self.location_verified:
			score -= 20
		
		# Deduct points for missing photos
		if not self.check_in_photo:
			score -= 10
		if not self.check_out_photo:
			score -= 10
		
		# Deduct points for excessive distance from site
		if self.distance_from_site and self.distance_from_site > 100:
			score -= min(30, int(self.distance_from_site / 50))
		
		# Bonus points for early entry or late exit (dedication)
		if self.early_entry:
			score += 5
		if self.late_exit:
			score += 5
		
		self.attendance_score = max(0, min(100, score))
	
	def sync_with_attendance(self):
		"""Sync with standard Attendance doctype"""
		if not self.attendance:
			# Create new attendance record
			attendance = frappe.new_doc("Attendance")
			attendance.employee = self.employee
			attendance.attendance_date = self.attendance_date
			attendance.status = self.status
			attendance.in_time = self.in_time
			attendance.out_time = self.out_time
			attendance.shift = self.shift
			
			try:
				attendance.insert()
				self.attendance = attendance.name
			except frappe.DuplicateEntryError:
				# Attendance already exists, link to it
				existing = frappe.db.get_value("Attendance", {
					"employee": self.employee,
					"attendance_date": self.attendance_date
				}, "name")
				self.attendance = existing
		else:
			# Update existing attendance
			attendance_doc = frappe.get_doc("Attendance", self.attendance)
			attendance_doc.status = self.status
			attendance_doc.in_time = self.in_time
			attendance_doc.out_time = self.out_time
			attendance_doc.save()
	
	@frappe.whitelist()
	def check_in(self, location=None, photo=None, device_info=None):
		"""Check in employee"""
		if self.in_time:
			frappe.throw("이미 체크인되었습니다.")
		
		now = frappe.utils.now()
		self.in_time = now
		self.status = "Present"
		
		if location:
			self.check_in_location = location
		if photo:
			self.check_in_photo = photo
		if device_info:
			self.device_info = device_info
		
		# Set IP address
		self.ip_address = frappe.local.request_ip if frappe.local.request_ip else ""
		
		# Check if early entry
		if self.shift:
			shift_doc = frappe.get_doc("Shift Type", self.shift)
			if shift_doc.start_time:
				shift_start = datetime.combine(
					datetime.strptime(str(self.attendance_date), "%Y-%m-%d").date(),
					shift_doc.start_time
				)
				check_in_time = datetime.strptime(str(self.in_time), "%Y-%m-%d %H:%M:%S")
				
				if check_in_time < shift_start:
					self.early_entry = 1
		
		self.save()
		return "체크인이 완료되었습니다."
	
	@frappe.whitelist()
	def check_out(self, location=None, photo=None):
		"""Check out employee"""
		if not self.in_time:
			frappe.throw("먼저 체크인을 해야 합니다.")
		
		if self.out_time:
			frappe.throw("이미 체크아웃되었습니다.")
		
		now = frappe.utils.now()
		self.out_time = now
		
		if location:
			self.check_out_location = location
		if photo:
			self.check_out_photo = photo
		
		# Check if late exit
		if self.shift:
			shift_doc = frappe.get_doc("Shift Type", self.shift)
			if shift_doc.end_time:
				shift_end = datetime.combine(
					datetime.strptime(str(self.attendance_date), "%Y-%m-%d").date(),
					shift_doc.end_time
				)
				check_out_time = datetime.strptime(str(self.out_time), "%Y-%m-%d %H:%M:%S")
				
				if check_out_time > shift_end:
					self.late_exit = 1
		
		self.save()
		return "체크아웃이 완료되었습니다."
	
	def get_location_status(self):
		"""Get location verification status"""
		if not self.check_in_location:
			return "No GPS Data"
		
		if self.location_verified:
			return "Verified"
		else:
			return f"Outside Range ({self.distance_from_site:.0f}m)"
	
	@frappe.whitelist()
	def get_mobile_summary(self):
		"""Get summary data for mobile view"""
		return {
			"employee_name": self.employee_name,
			"date": self.attendance_date,
			"status": self.status,
			"in_time": self.in_time,
			"out_time": self.out_time,
			"total_hours": self.total_working_hours,
			"location_status": self.get_location_status(),
			"attendance_score": self.attendance_score,
			"site_name": frappe.db.get_value("Customer Site", self.work_site, "site_name") if self.work_site else None
		}
