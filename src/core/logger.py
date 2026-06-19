import logging

def setup_logger():
    # Configure production-grade logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # TẮT LOG DEBUG RÁC TỪ CÁC THƯ VIỆN BÊN THỨ 3
    logging.getLogger('fontTools').setLevel(logging.INFO)
    logging.getLogger('weasyprint').setLevel(logging.INFO)
    
    return logging.getLogger("oss_release_tracker")
