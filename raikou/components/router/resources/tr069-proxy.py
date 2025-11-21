#!/usr/bin/env python3
"""
TR-069 MITM Proxy - Logging-only pass-through proxy
Forwards all TR-069 messages without modification and logs all traffic for debugging.
"""
import http.server
import socketserver
import urllib.request
import sys
import logging
import re

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
        # Read request body (CPE → ACS: Inform, TransferComplete, RebootResponse, etc.)
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length)
        
        client_ip = self.client_address[0]
        logger.info(f"Received POST from {client_ip}, path: {self.path}, size: {len(request_body)} bytes")
        
        # Log CPE requests for debugging
        if request_body and len(request_body) > 0:
            try:
                request_text = request_body.decode('utf-8', errors='ignore')
                # Extract RPC type from SOAP message
                rpc_match = re.search(r'<cwmp:(\w+)>|<(\w+) xmlns="urn:dslforum-org:cwmp-1-\d+">', request_text)
                if rpc_match:
                    rpc_type = rpc_match.group(1) or rpc_match.group(2)
                    logger.info(f"CPE → ACS: {rpc_type} RPC")
                    
                    # For SetParameterValuesResponse, log status code
                    if rpc_type == "SetParameterValuesResponse":
                        status_match = re.search(r'<Status[^>]*>(\d+)</Status>', request_text)
                        if status_match:
                            status_code = status_match.group(1)
                            status_msg = "SUCCESS" if status_code == "0" else f"FAILED (code: {status_code})"
                            logger.info(f"  SetParameterValuesResponse Status: {status_msg}")
                        else:
                            logger.info(f"  SetParameterValuesResponse (status not found)")
                    
                    # Log first 500 chars for debugging
                    logger.debug(f"Request preview: {request_text[:500]}...")
            except Exception as e:
                logger.debug(f"Could not parse request text: {e}")
        
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
                # Read ACS response (contains RPCs like Reboot, GetParameterValues, etc.)
                response_body = response.read()
                
                logger.info(f"Received response from ACS, size: {len(response_body)} bytes, status: {response.getcode()}")
                
                # Log ACS responses for debugging
                try:
                    response_text = response_body.decode('utf-8', errors='ignore')
                    # Extract RPC type from SOAP message
                    rpc_match = re.search(r'<cwmp:(\w+)>|<(\w+) xmlns="urn:dslforum-org:cwmp-1-\d+">', response_text)
                    if rpc_match:
                        rpc_type = rpc_match.group(1) or rpc_match.group(2)
                        logger.info(f"ACS → CPE: {rpc_type} RPC")
                        
                        # For SetParameterValues, log parameter names and values
                        if rpc_type == "SetParameterValues":
                            param_matches = re.findall(
                                r'<ParameterValueStruct>.*?<Name>(.*?)</Name>.*?<Value[^>]*>(.*?)</Value>.*?</ParameterValueStruct>',
                                response_text,
                                re.DOTALL
                            )
                            if param_matches:
                                for name, value in param_matches:
                                    # Truncate long values (like passwords)
                                    display_value = value[:50] + "..." if len(value) > 50 else value
                                    logger.info(f"  SetParameter: {name} = {display_value}")
                        
                        # Log first 500 chars for debugging
                        logger.debug(f"Response preview: {response_text[:500]}...")
                except Exception as e:
                    logger.debug(f"Could not parse response text: {e}")
                
                # Forward response to CPE (pass-through, no modification)
                self.send_response(response.getcode())
                for header, value in response.headers.items():
                    header_lower = header.lower()
                    if header_lower not in ['connection', 'transfer-encoding', 'content-encoding', 'content-length']:
                        self.send_header(header, value)
                # Set Content-Length
                self.send_header('Content-Length', str(len(response_body)))
                self.end_headers()
                self.wfile.write(response_body)
                
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
    logger.info("Mode: LOGGING-ONLY - All messages pass through unchanged, traffic logged for debugging")
    
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

