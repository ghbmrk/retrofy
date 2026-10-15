"""Explainable research routing. Format recognition never implies compatibility."""
from pathlib import Path
import hashlib

LIMIT=64*1024*1024

def identify(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file(): raise ValueError('Require regular non-symlink file')
    sha=hashlib.sha256(); total=0; head=b''
    with p.open('rb') as f:
        while True:
            b=f.read(65536)
            if not b: break
            if not head: head=b[:4096]
            total+=len(b)
            if total>LIMIT: raise ValueError('64 MiB identification limit; use a versioned manifest for larger installs')
            sha.update(b)
    kind='unknown'; route='manual format research'
    if head.startswith(b'MZ'): kind='DOS/PE candidate'; route='validate PE/DOS header; Ghidra static analysis plus isolated runtime traces'
    elif head.startswith(b'\x7fELF'): kind='ELF candidate'; route='validate ELF ABI; disassembly plus isolated syscall/input traces'
    elif head[:4] in (b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xca\xfe\xba\xbe'):
        kind='Mach-O/fat candidate'; route='validate slices/signatures; static analysis plus isolated platform capture'
    elif head.startswith(b'PK\x03\x04'): kind='ZIP candidate'; route='bounded archive index and engine identification, not automatic extraction'
    elif p.suffix.lower()=='.xsb': kind='XSB candidate'; route='strict single-board parser and declared mechanics review'
    return dict(schema=1,sha256=sha.hexdigest(),bytes=total,format_hint=kind,route=route,
        decision='unresolved',reason='Signature/extension is not semantic or control evidence',
        executed=False,uploaded=False)

def controls(candidate):
    """A conservative prefilter over declarations, not an ergonomic assessment."""
    axes=candidate.get('independent_directional_axes')
    buttons=candidate.get('simultaneous_non_directional_actions')
    if type(axes) is not int or type(buttons) is not int or min(axes,buttons)<0:
        return dict(decision='unresolved',reason='Missing/nonnegative integer control declarations')
    if axes>1: return dict(decision='reject',reason='Independent movement and aiming cannot both map directly to one D-pad')
    if buttons>2: return dict(decision='reject',reason='Required simultaneous actions exceed A/B without chords or modes')
    for key in ('pointer_precision_required','text_entry_required','external_service_required'):
        if candidate.get(key) is True: return dict(decision='reject',reason=key)
        if candidate.get(key) is not False: return dict(decision='unresolved',reason='Missing evidence: '+key)
    return dict(decision='unresolved',reason='Control capacity fits; timing, readability, workload and observed usability still untested')
