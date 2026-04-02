"""Read and parse network scan (arp-scan) results."""
import os
import pathlib

def is_ip_address(ip: str) -> bool:
    """Check if the given string is an IP address."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        if not 0 <= int(part) <= 255:
            return False
    return True

def read_network_scan() -> list[dict]:
    """Read network scan results from file and parse the results."""
    try:
        folder = pathlib.Path(__file__).parent.parent
        with open(folder / "network_scan.txt", 'r') as file:
            lines = file.readlines()
    except:
        return []

    results = []
    for line in lines:
        split_line = line.split()
        if not split_line or not is_ip_address(split_line[0]):
            continue

        results.append({
            "ip": split_line[0],
            "mac": split_line[1],
            "company": " ".join(split_line[2:])
        })

    return results

if __name__ == '__main__':
    print(read_network_scan())
