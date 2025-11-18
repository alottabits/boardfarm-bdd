#!/usr/bin/env python3
"""
TR-069 MITM Proxy - Pass-through implementation
Forwards all TR-069 messages without modification (for compatibility testing)
"""
import http.server
import socketserver
import urllib.request
import sys
import logging

# Configuration
ACS_HOST = "172.25.1.40"
ACS_PORT = 7547
PROXY_PORT = 8754  # Changed from 87547 to avoid iptables-legacy port validation issues

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TR069ProxyHandler(http.server.BaseHTTPRequestHandler):
    """HTTP proxy handler for TR-069 traffic"""
    
    def handle(self):
        """Override handle to add connection logging"""
        client_ip = self.client_address[0]
        logger.info(f"New connection from {client_ip}")
        try:
            super().handle()
        except Exception as e:
            logger.error(f"Error handling connection from {client_ip}: {e}", exc_info=True)
        finally:
            logger.debug(f"Connection from {client_ip} closed")
    
    def do_POST(self):
        """Handle HTTP POST requests (TR-069 uses POST for all RPCs)"""
        # Read request body (CPE → ACS: Inform, TransferComplete, etc.)
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length)
        
        client_ip = self.client_address[0]
        logger.info(f"Received POST from {client_ip}, path: {self.path}, size: {len(request_body)} bytes")
        
        # Log CPE responses (especially DownloadResponse with faults)
        if request_body and len(request_body) > 0:
            try:
                request_text = request_body.decode('utf-8', errors='ignore')
                if 'DownloadResponse' in request_text or 'Fault' in request_text:
                    logger.info("=" * 80)
                    logger.info("CPE RESPONSE DETECTED:")
                    logger.info(request_text[:1000])  # First 1000 chars
                    logger.info("=" * 80)
            except:
                pass
        
        # Forward request to ACS (pass-through, no modification)
        try:
            target_url = f"http://{ACS_HOST}:{ACS_PORT}{self.path}"
            req = urllib.request.Request(
                target_url,
                data=request_body,
                headers=dict(self.headers)
            )
            req.add_header('Content-Length', str(len(request_body)))
            # Remove hop-by-hop headers
            if 'Connection' in req.headers:
                req.remove_header('Connection')
            if 'Keep-Alive' in req.headers:
                req.remove_header('Keep-Alive')
            
            logger.debug(f"Forwarding request to {target_url}")
            
            with urllib.request.urlopen(req, timeout=30) as response:
                # Read ACS response (contains Download RPCs, GetParameterValues, etc.)
                response_body = response.read()
                
                logger.info(f"Received response from ACS, size: {len(response_body)} bytes, status: {response.getcode()}")
                
                # Modify response if it contains Download RPC (remove empty optional parameters)
                modified_response = response_body
                try:
                    response_text = response_body.decode('utf-8', errors='ignore')
                    if '<cwmp:Download>' in response_text or 'Download' in response_text:
                        logger.info("=" * 80)
                        logger.info("DOWNLOAD RPC DETECTED - Modifying for PrplOS compatibility")
                        logger.info("=" * 80)
                        
                        # Remove empty optional parameters that PrplOS rejects
                        # Based on investigation: PrplOS rejects empty TargetFileName, FileSize, SuccessURL, FailureURL
                        import re
                        
                        # Log original for debugging
                        logger.info(f"Original response size: {len(response_text)} bytes")
                        original_download = re.search(r'<cwmp:Download>.*?</cwmp:Download>', response_text, re.DOTALL)
                        if original_download:
                            logger.info("ORIGINAL Download RPC:")
                            logger.info(original_download.group(0))
                        
                        # Remove empty TargetFileName tag (handle both namespace-qualified and unqualified)
                        # Pattern: <cwmp:TargetFileName></cwmp:TargetFileName> or <TargetFileName></TargetFileName>
                        response_text = re.sub(r'<cwmp:TargetFileName>\s*</cwmp:TargetFileName>', '', response_text)
                        response_text = re.sub(r'<cwmp:TargetFileName></cwmp:TargetFileName>', '', response_text)
                        response_text = re.sub(r'<cwmp:TargetFileName\s*/>', '', response_text)
                        response_text = re.sub(r'<TargetFileName>\s*</TargetFileName>', '', response_text)
                        response_text = re.sub(r'<TargetFileName></TargetFileName>', '', response_text)
                        response_text = re.sub(r'<TargetFileName\s*/>', '', response_text)
                        
                        # Remove FileSize tag completely (PrplOS doesn't support this parameter at all)
                        # Handle both namespace-qualified and unqualified
                        response_text = re.sub(r'<cwmp:FileSize>.*?</cwmp:FileSize>', '', response_text, flags=re.DOTALL)
                        response_text = re.sub(r'<cwmp:FileSize\s*/>', '', response_text)
                        response_text = re.sub(r'<FileSize>.*?</FileSize>', '', response_text, flags=re.DOTALL)
                        response_text = re.sub(r'<FileSize\s*/>', '', response_text)
                        
                        # Remove empty SuccessURL tag
                        response_text = re.sub(r'<cwmp:SuccessURL>\s*</cwmp:SuccessURL>', '', response_text)
                        response_text = re.sub(r'<cwmp:SuccessURL></cwmp:SuccessURL>', '', response_text)
                        response_text = re.sub(r'<cwmp:SuccessURL\s*/>', '', response_text)
                        response_text = re.sub(r'<SuccessURL>\s*</SuccessURL>', '', response_text)
                        response_text = re.sub(r'<SuccessURL></SuccessURL>', '', response_text)
                        response_text = re.sub(r'<SuccessURL\s*/>', '', response_text)
                        
                        # Remove empty FailureURL tag
                        response_text = re.sub(r'<cwmp:FailureURL>\s*</cwmp:FailureURL>', '', response_text)
                        response_text = re.sub(r'<cwmp:FailureURL></cwmp:FailureURL>', '', response_text)
                        response_text = re.sub(r'<cwmp:FailureURL\s*/>', '', response_text)
                        response_text = re.sub(r'<FailureURL>\s*</FailureURL>', '', response_text)
                        response_text = re.sub(r'<FailureURL></FailureURL>', '', response_text)
                        response_text = re.sub(r'<FailureURL\s*/>', '', response_text)
                        
                        # Remove empty Username/Password if present (optional)
                        response_text = re.sub(r'<cwmp:Username>\s*</cwmp:Username>', '', response_text)
                        response_text = re.sub(r'<cwmp:Username></cwmp:Username>', '', response_text)
                        response_text = re.sub(r'<Username>\s*</Username>', '', response_text)
                        response_text = re.sub(r'<Username></Username>', '', response_text)
                        response_text = re.sub(r'<cwmp:Password>\s*</cwmp:Password>', '', response_text)
                        response_text = re.sub(r'<cwmp:Password></cwmp:Password>', '', response_text)
                        response_text = re.sub(r'<Password>\s*</Password>', '', response_text)
                        response_text = re.sub(r'<Password></Password>', '', response_text)
                        
                        logger.info(f"Modified response size: {len(response_text)} bytes")
                        
                        # Verify modification worked
                        if '<TargetFileName>' in response_text or '<FileSize>' in response_text:
                            logger.warning("WARNING: Modification may have failed - still contains problematic tags!")
                            logger.warning(f"Contains TargetFileName: {'<TargetFileName>' in response_text}")
                            logger.warning(f"Contains FileSize: {'<FileSize>' in response_text}")
                        else:
                            logger.info("✓ Modification verified: All problematic tags removed")
                        
                        modified_response = response_text.encode('utf-8')
                        
                        # Log the modified Download RPC
                        download_match = re.search(r'<cwmp:Download>.*?</cwmp:Download>', response_text, re.DOTALL)
                        if download_match:
                            logger.info("MODIFIED Download RPC:")
                            logger.info(download_match.group(0))
                        
                        # Log a snippet of the full SOAP envelope to verify structure
                        soap_body_match = re.search(r'<soap:Body>.*?</soap:Body>', response_text, re.DOTALL)
                        if soap_body_match:
                            logger.info("SOAP Body structure (first 500 chars):")
                            logger.info(soap_body_match.group(0)[:500])
                        
                        logger.info("=" * 80)
                        
                except Exception as e:
                    logger.error(f"Error modifying Download RPC: {e}", exc_info=True)
                    # On error, use original response
                    modified_response = response_body
                
                # Forward modified response to CPE
                self.send_response(response.getcode())
                for header, value in response.headers.items():
                    header_lower = header.lower()
                    if header_lower not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length']:
                        self.send_header(header, value)
                # Set Content-Length (use modified response length)
                self.send_header('Content-Length', str(len(modified_response)))
                self.end_headers()
                self.wfile.write(modified_response)
                
                logger.debug(f"Forwarded response to {client_ip}")
                
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error from ACS: {e.code} {e.reason}")
            self.send_error(e.code, f"Proxy error: {e.reason}")
        except urllib.error.URLError as e:
            logger.error(f"URL error: {e.reason}")
            self.send_error(502, f"Proxy error: Cannot reach ACS - {e.reason}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            self.send_error(502, f"Proxy error: {e}")
    
    def log_message(self, format, *args):
        """Override default logging to use our logger"""
        logger.debug(f"{self.address_string()} - {format % args}")
    
    def handle_one_request(self):
        """Override to catch and log all request handling"""
        try:
            return super().handle_one_request()
        except BrokenPipeError:
            logger.warning(f"Broken pipe from {self.client_address[0]}")
            return False
        except Exception as e:
            logger.error(f"Error in handle_one_request: {e}", exc_info=True)
            return False


def main():
    """Start the TR-069 proxy server"""
    logger.info(f"TR-069 MITM Proxy starting on port {PROXY_PORT}")
    logger.info(f"Forwarding to ACS at {ACS_HOST}:{ACS_PORT}")
    logger.info("Mode: ACTIVE - Removing empty/unsupported parameters from Download RPCs")
    
    try:
        with socketserver.TCPServer(("0.0.0.0", PROXY_PORT), TR069ProxyHandler) as httpd:
            logger.info(f"Proxy listening on 0.0.0.0:{PROXY_PORT}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down proxy...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

