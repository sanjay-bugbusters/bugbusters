ISSUE_PATTERNS = {
    "kafka": {
        "duplicates": {
            "patterns": [
                r"kafka.*duplicate.*messages",
                r"duplicate.*kafka.*messages",
                r"message.*processed.*twice",
                r"duplicate.*processing"
            ],
            "root_causes": [
                "Consumer group rebalancing causing message reprocessing",
                "Multiple consumer instances with same group.id",
                "Network issues causing offset commit failures",
                "Manual offset reset or incorrect offset management",
                "Producer retries due to network issues",
                "Incorrect idempotence configuration"
            ],
            "solutions": [
                "Implement idempotent processing using unique message IDs",
                "Configure proper consumer group IDs",
                "Enable producer idempotence",
                "Implement deduplication logic",
                "Monitor and handle consumer group rebalancing properly",
                "Ensure proper offset commit strategy"
            ]
        },
        "connection": {
            "patterns": [
                r"kafka.*connection.*failed",
                r"cannot.*connect.*kafka",
                r"broker.*unreachable"
            ],
            "root_causes": [
                "Network connectivity issues",
                "Invalid broker configuration",
                "Security/authentication failures"
            ],
            "solutions": [
                "Verify network connectivity",
                "Check broker configuration",
                "Validate security credentials"
            ]
        }
    },
    "mongodb": {
        "connection": {
            "patterns": [
                r"mongodb.*connection.*failed",
                r"cannot.*connect.*mongo",
                r"mongodb.*timeout"
            ],
            "root_causes": [
                "Network connectivity issues",
                "Invalid connection string",
                "Authentication failures"
            ],
            "solutions": [
                "Check network connectivity",
                "Verify connection string",
                "Validate credentials"
            ]
        }
    }
}
