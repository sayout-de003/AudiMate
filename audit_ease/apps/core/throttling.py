from rest_framework.throttling import ScopedRateThrottle

class PDFGenerationThrottle(ScopedRateThrottle):
    scope = 'pdf_generation'
