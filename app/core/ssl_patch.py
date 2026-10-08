import os
import certifi

def apply_ssl_fix():
    """Garante que as variáveis de ambiente de certificados SSL usam o certifi cacert.pem,
    evitando SSLCertVerificationError no Windows para requests, httpx e aiohttp."""
    ca_bundle = certifi.where()
    os.environ["SSL_CERT_FILE"] = ca_bundle
    os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
    os.environ["CURL_CA_BUNDLE"] = ca_bundle

    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass
