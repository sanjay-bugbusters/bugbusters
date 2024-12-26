package com.bugbusters.prototype.controller;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("v1/api/bugbusters")
public class BugBustersController {
	
	// Get mapping for health status with 200 OK response code 
	@GetMapping
	@ResponseStatus(HttpStatus.OK)
	public String healthCheck() {
		return "UP"; 
	}
}
