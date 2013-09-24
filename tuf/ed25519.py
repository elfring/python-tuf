"""
<Program Name>
  ed25519.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  September 24, 2013.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  The goal of this module is to support ed25519 signatures.  ed25519 is an
  elliptic-curve public key signature scheme, where the signature fits into
  64 bytes and the public key has a length of only 32 bytes.
  http://ed25519.cr.yp.to/
  
  'tuf/ed25519.py' calls 'ed25519/ed25519.py', which is the Python
  implementation of ed25519 provided by the author.
  http://ed25519.cr.yp.to/software.html
  
  The ed25519-related functions provided include generate(), create_signature(),
  and verify_signature().  The 'ed25519' package used by this module
  generates the actual ed25519 keys and the functions listed above can be viewed
  as an easy-to-use public interface.  Additional functions contained here
  include create_in_metadata_format() and create_from_metadata_format().  These
  last two functions produce or use ed25519 keys compatible with the key
  structures listed in TUF Metadata files.  The generate() function returns a
  dictionary containing all the information needed of ed25519 keys, such as
  public and private keys, keyIDs, and an idenfier.  create_signature() and
  verify_signature() are supplemental functions used for generating ed25519
  signatures and verifying them.
  
  Key IDs are used as identifiers for keys (e.g., RSA key).  They are the
  hexadecimal representation of the hash of key object (specifically, the key
  object containing only the public key).  Review 'rsa_key.py' and the
  '_get_keyid()' function to see precisely how keyids are generated.  One may
  get the keyid of a key object by simply accessing the dictionary's 'keyid'
  key (i.e., rsakey['keyid']).

 """

# Required for hexadecimal conversions.  Signatures are hexlified.
import binascii

# Generate OS-specific randomness suitable for cryptographic use.
# http://docs.python.org/2/library/os.html#miscellaneous-functions
import os.urandom

# Import the python implementation of the ed25519 algorithm that is provided by
# the author.  Note: This implementation is very slow and does not include
# protection against side-channel attacks.  Verifying signatures can take
# approximately 5 seconds on a intel core 2 duo @ 2.2 ghz x 2). 
# http://ed25519.cr.yp.to/software.html   
import ed25519

import tuf

# Digest objects needed to generate hashes.
import tuf.hash

# Perform object format-checking.
import tuf.formats


def generate():
  """
  <Purpose> 
    Generate ed25519's public key ('pk') and seed key ('sk').
    In addition, a keyid used as an identifier for ed25519 keys is generated.
    The object returned conforms to 'tuf.formats.ED25519KEY_SCHEMA' and
    has the form:
    {'keytype': 'ed25519',
     'keyid': keyid,
     'keyval': {'public': '\xb3\x17c\xda\x80\xed`F\xcc\xe4 ...',
                'private': '\xd7D\xb9b\xdf\xf6*\xa1\xbb\x19 ...'}}
    
    The public and private keys are strings.  An ed25519 seed key is a random
    32-byte value.  Public keys are also 32 bytes.

  <Arguments>
    None.

  <Exceptions>
    NotImplementedError, if a randomness source is not found.

    ValueError, if an exception occurs after calling the RSA key generation
    routine.  'bits' must be a multiple of 256.  The 'ValueError' exception is
    raised by the key generation function of the cryptography library called.

    tuf.FormatError, if 'bits' does not contain the correct format.

  <Side Effects>
    The ed25519 keys are generated by first generating a random 32-byte value
    'sk' with os.urandom() and then calling ed25519's ed25519.25519.publickey(sk).

  <Returns>
    A dictionary containing the ed25519 keys and other identifying information.
    Conforms to 'tuf.formats.ED25519KEY_SCHEMA'.
  
  """

  
  # Begin building the ed25519 key dictionary. 
  ed25519_key_dict = {}
  keytype = 'ed25519'
 
  # Generate ed25519's seed key by calling os.urandom().  The random bytes
  # returned should be suitable for cryptographic use and is OS-specific.
  # Raise 'NotImplementedError' if a randomness source is not found.
  # ed25519 seed keys are fixed at 32 bytes (256-bit keys).
  ed25519_seed_key = os.urandom(32)

  # Generate the public key.  The 'ed25519.ed25519.py' module performs
  # the actual key generation.
  ed25519_public_key = ed25519.ed25519.publickey(seed_key)
  
  # Generate the keyid for the ed25519 key dict.  'key_value' corresponds to the
  # 'keyval' entry of the 'ED25519KEY_SCHEMA' dictionary.  The seed key
  # information is not included in the generation of the 'keyid' identifier.
  key_value = {'public': ed25519_public_key,
               'private': ''}
  keyid = _get_keyid(key_value)

  # Build the 'ed25519_key_dict' dictionary.  Update 'key_value' with the
  # ed25519 seed key prior to adding 'key_value' to 'ed25519_key_dict'.
  key_value['private'] = ed25519_seed_key 

  ed25519_key_dict['keytype'] = keytype
  ed25519_key_dict['keyid'] = keyid
  ed25519_key_dict['keyval'] = key_value

  return ed25519_key_dict





def create_in_metadata_format(key_value, private=False):
  """
  <Purpose>
    Return a dictionary conformant to 'tuf.formats.KEY_SCHEMA'.
    If 'private' is True, include the private key.  The dictionary
    returned has the form:
    {'keytype': 'rsa',
     'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}
    
    or if 'private' is False:

    {'keytype': 'rsa',
     'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                'private': ''}}
    
    The private and public keys are in PEM format.
    
    RSA keys are stored in Metadata files (e.g., root.txt) in the format
    returned by this function.
  
  <Arguments>
    key_value:
      A dictionary containing a private and public RSA key.
      'key_value' is of the form:

      {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
       'private': '-----BEGIN RSA PRIVATE KEY----- ...'}},
      conformat to 'tuf.formats.KEYVAL_SCHEMA'.

    private:
      Indicates if the private key should be included in the
      returned dictionary.

  <Exceptions>
    tuf.FormatError, if 'key_value' does not conform to 
    'tuf.formats.KEYVAL_SCHEMA'.

  <Side Effects>
    None.

  <Returns>
    An 'KEY_SCHEMA' dictionary.

  """
	

  # Does 'key_value' have the correct format?
  # This check will ensure 'key_value' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.KEYVAL_SCHEMA.check_match(key_value)

  if private is True and key_value['private']:
    return {'keytype': 'rsa', 'keyval': key_value}
  else:
    public_key_value = {'public': key_value['public'], 'private': ''}
    return {'keytype': 'ed25519', 'keyval': public_key_value}





def create_from_metadata_format(key_metadata):
  """
  <Purpose>
    Construct an RSA key dictionary (i.e., tuf.formats.RSAKEY_SCHEMA)
    from 'key_metadata'.  The dict returned by this function has the exact
    format as the dict returned by generate().  It is of the form:
   
    {'keytype': 'rsa',
     'keyid': keyid,
     'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}

    The public and private keys are in PEM format and stored as strings.

    RSA key dictionaries in RSAKEY_SCHEMA format should be used by
    modules storing a collection of keys, such as a keydb and keystore.
    RSA keys as stored in metadata files use a different format, so this 
    function should be called if an RSA key is extracted from one of these 
    metadata files and needs converting.  Generate() creates an entirely
    new key and returns it in the format appropriate for 'keydb.py' and
    'keystore.py'.

  <Arguments>
    key_metadata:
      The RSA key dictionary as stored in Metadata files, conforming to
      'tuf.formats.KEY_SCHEMA'.  It has the form:
      
      {'keytype': '...',
       'keyval': {'public': '...',
                  'private': '...'}}

  <Exceptions>
    tuf.FormatError, if 'key_metadata' does not conform to
    'tuf.formats.KEY_SCHEMA'.

  <Side Effects>
    None.

  <Returns>
    A dictionary containing the RSA keys and other identifying information.

  """


  # Does 'key_metadata' have the correct format?
  # This check will ensure 'key_metadata' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.KEY_SCHEMA.check_match(key_metadata)

  # Construct the dictionary to be returned.
  rsakey_dict = {}
  keytype = 'ed25519'
  key_value = key_metadata['keyval']

  # Convert 'key_value' to 'tuf.formats.KEY_SCHEMA' and generate its hash
  # The hash is in hexdigest form. 
  keyid = _get_keyid(key_value)

  # We now have all the required key values.  Build 'rsakey_dict'.
  rsakey_dict['keytype'] = keytype
  rsakey_dict['keyid'] = keyid
  rsakey_dict['keyval'] = key_value

  return rsakey_dict





def _get_keyid(key_value):
  """Return the keyid for 'key_value'."""

  # 'keyid' will be generated from an object conformant to KEY_SCHEMA,
  # which is the format Metadata files (e.g., root.txt) store keys.
  # 'create_in_metadata_format()' returns the object needed by _get_keyid().
  rsakey_meta = create_in_metadata_format(key_value, private=False)

  # Convert the RSA key to JSON Canonical format suitable for adding
  # to digest objects.
  rsakey_update_data = tuf.formats.encode_canonical(rsakey_meta)

  # Create a digest object and call update(), using the JSON 
  # canonical format of 'rskey_meta' as the update data.
  digest_object = tuf.hash.digest(_KEY_ID_HASH_ALGORITHM)
  digest_object.update(rsakey_update_data)

  # 'keyid' becomes the hexadecimal representation of the hash.  
  keyid = digest_object.hexdigest()

  return keyid





def create_signature(rsakey_dict, data):
  """
  <Purpose>
    Return a signature dictionary of the form:
    {'keyid': keyid,
     'method': 'PyCrypto-PKCS#1 PPS',
     'sig': sig}.

    The signing process will use the private key
    rsakey_dict['keyval']['private'] and 'data' to generate the signature.

    RFC3447 - RSASSA-PSS 
    http://www.ietf.org/rfc/rfc3447.txt

  <Arguments>
    rsakey_dict:
      A dictionary containing the RSA keys and other identifying information.
      'rsakey_dict' has the form:
    
      {'keytype': 'ed25519',
       'keyid': keyid,
       'keyval': {'public': '',
                  'private': ''}}

      The public and private keys are in PEM format and stored as strings.

    data:
      Data object used by create_signature() to generate the signature.

  <Exceptions>
    TypeError, if a private key is not defined for 'rsakey_dict'.

    tuf.FormatError, if an incorrect format is found for the
    'rsakey_dict' object.

  <Side Effects>
    PyCrypto's 'Crypto.Signature.PKCS1_PSS' called to perform the actual
    signing.

  <Returns>
    A signature dictionary conformat to 'tuf.format.SIGNATURE_SCHEMA'.

  """


  # Does 'rsakey_dict' have the correct format?
  # This check will ensure 'rsakey_dict' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.RSAKEY_SCHEMA.check_match(rsakey_dict)

  # Signing the 'data' object requires a private key.
  # The 'PyCrypto-PKCS#1 PSS' (i.e., PyCrypto module) signing method is the
  # only method currently supported.
  signature = {}
  private_key = rsakey_dict['keyval']['private']
  keyid = rsakey_dict['keyid']
  method = 'PyCrypto-PKCS#1 PSS'
  sig = None
 
  # Verify the signature, but only if the private key has been set.  The private
  # key is a NULL string if unset.  Although it may be clearer to explicit check
  # that 'private_key' is not '', we can/should check for a value and not
  # compare identities with the 'is' keyword. 
  if len(private_key):
    # Calculate the SHA256 hash of 'data' and generate the hash's PKCS1-PSS
    # signature. 
    try:
      rsa_key_object = Crypto.PublicKey.RSA.importKey(private_key)
      sha256_object = Crypto.Hash.SHA256.new(data)
      pkcs1_pss_signer = Crypto.Signature.PKCS1_PSS.new(rsa_key_object)
      sig = pkcs1_pss_signer.sign(sha256_object)
    except (ValueError, IndexError, TypeError), e:
      message = 'An RSA signature could not be generated.'
      raise tuf.CryptoError(message)
  else:
    raise TypeError('The required private key is not defined for "rsakey_dict".')

  # Build the signature dictionary to be returned.
  # The hexadecimal representation of 'sig' is stored in the signature.
  signature['keyid'] = keyid
  signature['method'] = method
  signature['sig'] = binascii.hexlify(sig)

  return signature





def verify_signature(rsakey_dict, signature, data):
  """
  <Purpose>
    Determine whether the private key belonging to 'rsakey_dict' produced
    'signature'.  verify_signature() will use the public key found in
    'rsakey_dict', the 'method' and 'sig' objects contained in 'signature',
    and 'data' to complete the verification.  Type-checking performed on both
    'rsakey_dict' and 'signature'.

  <Arguments>
    rsakey_dict:
      A dictionary containing the RSA keys and other identifying information.
      'rsakey_dict' has the form:
     
      {'keytype': 'rsa',
       'keyid': keyid,
       'keyval': {'public': '-----BEGIN RSA PUBLIC KEY----- ...',
                  'private': '-----BEGIN RSA PRIVATE KEY----- ...'}}

      The public and private keys are in PEM format and stored as strings.
      
    signature:
      The signature dictionary produced by tuf.rsa_key.create_signature().
      'signature' has the form:
      {'keyid': keyid, 'method': 'method', 'sig': sig}.  Conformant to
      'tuf.formats.SIGNATURE_SCHEMA'.
      
    data:
      Data object used by tuf.rsa_key.create_signature() to generate
      'signature'.  'data' is needed here to verify the signature.

  <Exceptions>
    tuf.UnknownMethodError.  Raised if the signing method used by
    'signature' is not one supported by tuf.rsa_key.create_signature().
    
    tuf.FormatError. Raised if either 'rsakey_dict'
    or 'signature' do not match their respective tuf.formats schema.
    'rsakey_dict' must conform to 'tuf.formats.RSAKEY_SCHEMA'.
    'signature' must conform to 'tuf.formats.SIGNATURE_SCHEMA'.

  <Side Effects>
    Crypto.Signature.PKCS1_PSS.verify() called to do the actual verification.

  <Returns>
    Boolean.  True if the signature is valid, False otherwise.

  """


  # Does 'rsakey_dict' have the correct format?
  # This check will ensure 'rsakey_dict' has the appropriate number
  # of objects and object types, and that all dict keys are properly named.
  # Raise 'tuf.FormatError' if the check fails.
  tuf.formats.RSAKEY_SCHEMA.check_match(rsakey_dict)

  # Does 'signature' have the correct format?
  tuf.formats.SIGNATURE_SCHEMA.check_match(signature)

  # Using the public key belonging to 'rsakey_dict'
  # (i.e., rsakey_dict['keyval']['public']), verify whether 'signature'
  # was produced by rsakey_dict's corresponding private key
  # rsakey_dict['keyval']['private'].  Before returning the Boolean result,
  # ensure 'PyCrypto-PKCS#1 PSS' was used as the signing method.
  method = signature['method']
  sig = signature['sig']
  public_key = rsakey_dict['keyval']['public']
  valid_signature = False

  if method == 'PyCrypto-PKCS#1 PSS':
    try:
      rsa_key_object = Crypto.PublicKey.RSA.importKey(public_key)
      pkcs1_pss_verifier = Crypto.Signature.PKCS1_PSS.new(rsa_key_object)
      sha256_object = Crypto.Hash.SHA256.new(data)
      
      # The metadata stores signatures in hex.  Unhexlify and verify the
      # signature.
      signature = binascii.unhexlify(sig)
      valid_signature = pkcs1_pss_verifier.verify(sha256_object, signature)
    except (ValueError, IndexError, TypeError), e:
      message = 'The RSA signature could not be verified.'
      raise tuf.CryptoError(message)
  else:
    raise tuf.UnknownMethodError(method)

  return valid_signature 
