# import os
# import re
# import sys
# import urllib.request
# import urllib.error
# import xml.etree.ElementTree as ET

# NEXUS_BASE_URL = os.environ["NEXUS_BASE_URL"].rstrip("/")
# NEXUS_USER = os.environ["NEXUS_USER"]
# NEXUS_PASS = os.environ["NEXUS_PASS"]

# GROUP_ID = os.environ["BOM_GROUP_ID"]
# ARTIFACT_ID = os.environ["BOM_ARTIFACT_ID"]

# POM_FILE = os.environ.get("POM_FILE", "pom.xml")


# def fail(message):
#     print(f"::error::{message}")
#     sys.exit(1)


# def version_key(version):
#     """
#     POC version comparison.

#     Supports versions such as:
#       1.0.0
#       1.0.5
#       1.0.6
#       2.0.0

#     For the current POC this is sufficient because the BOM
#     versions are numeric release versions.
#     """
#     if not re.fullmatch(r"\d+(?:\.\d+)*", version):
#         fail(
#             f"Unsupported version format '{version}'. "
#             "This watcher currently expects numeric Maven release versions."
#         )

#     return tuple(int(part) for part in version.split("."))


# def get_nexus_metadata():
#     group_path = GROUP_ID.replace(".", "/")

#     metadata_url = (
#         f"{NEXUS_BASE_URL}"
#         f"/repository/maven-releases/"
#         f"{group_path}/"
#         f"{ARTIFACT_ID}/"
#         f"maven-metadata.xml"
#     )

#     print(f"Checking Nexus metadata:")
#     print(metadata_url)

#     credentials = f"{NEXUS_USER}:{NEXUS_PASS}".encode()

#     request = urllib.request.Request(
#         metadata_url,
#         headers={
#             "Authorization": "Basic "
#                              + __import__("base64").b64encode(credentials).decode(),
#             "Accept": "application/xml",
#         },
#     )

#     try:
#         with urllib.request.urlopen(request, timeout=30) as response:
#             if response.status != 200:
#                 fail(
#                     f"Nexus returned HTTP {response.status}"
#                 )

#             return response.read()

#     except urllib.error.HTTPError as exc:
#         fail(
#             f"Nexus returned HTTP {exc.code} while reading "
#             f"maven-metadata.xml"
#         )

#     except urllib.error.URLError as exc:
#         fail(f"Unable to reach Nexus: {exc.reason}")


# def get_latest_version(metadata):
#     try:
#         root = ET.fromstring(metadata)
#     except ET.ParseError as exc:
#         fail(f"Invalid Maven metadata XML: {exc}")

#     versions = [
#         version.text.strip()
#         for version in root.findall("./versioning/versions/version")
#         if version.text and version.text.strip()
#     ]

#     if not versions:
#         fail("No versions were found in Nexus metadata.")

#     latest = max(versions, key=version_key)

#     return latest


# def get_current_version():
#     try:
#         tree = ET.parse(POM_FILE)
#     except FileNotFoundError:
#         fail(f"POM file not found: {POM_FILE}")
#     except ET.ParseError as exc:
#         fail(f"Invalid POM XML: {exc}")

#     root = tree.getroot()

#     namespace = {"m": "http://maven.apache.org/POM/4.0.0"}

#     for dependency in root.findall(
#             ".//m:dependencyManagement/m:dependencies/m:dependency",
#             namespace,
#     ):
#         group = dependency.find("m:groupId", namespace)
#         artifact = dependency.find("m:artifactId", namespace)
#         version = dependency.find("m:version", namespace)

#         if (
#                 group is not None
#                 and artifact is not None
#                 and version is not None
#                 and group.text == GROUP_ID
#                 and artifact.text == ARTIFACT_ID
#         ):
#             return version.text.strip()

#     fail(
#         f"Could not find dependency "
#         f"{GROUP_ID}:{ARTIFACT_ID} "
#         f"in {POM_FILE}"
#     )


# def update_pom(current_version, latest_version):
#     with open(POM_FILE, "r", encoding="utf-8") as file:
#         content = file.read()

#     # Find the dependency block containing our BOM.
#     dependency_pattern = re.compile(
#         r"<dependency>\s*"
#         r"<groupId>\s*" + re.escape(GROUP_ID) + r"\s*</groupId>\s*"
#                                                 r"<artifactId>\s*" + re.escape(ARTIFACT_ID) + r"\s*</artifactId>"
#                                                                                               r"(?P<rest>.*?)"
#                                                                                               r"</dependency>",
#         re.DOTALL,
#         )

#     match = dependency_pattern.search(content)

#     if not match:
#         fail(
#             f"Could not find dependency "
#             f"{GROUP_ID}:{ARTIFACT_ID} in {POM_FILE}"
#         )

#     dependency_block = match.group(0)

#     # Find the version inside that dependency block.
#     version_pattern = re.compile(
#         r"(<version>\s*)"
#         + re.escape(current_version)
#         + r"(\s*</version>)"
#     )

#     updated_dependency_block, version_count = version_pattern.subn(
#         rf"\g<1>{latest_version}\g<2>",
#         dependency_block,
#         count=1,
#     )

#     if version_count != 1:
#         fail(
#             f"Found {GROUP_ID}:{ARTIFACT_ID}, but could not find "
#             f"version {current_version} inside its dependency block."
#         )

#     updated_content = content.replace(
#         dependency_block,
#         updated_dependency_block,
#         1,
#     )

#     with open(POM_FILE, "w", encoding="utf-8") as file:
#         file.write(updated_content)

#     print(
#         f"Successfully updated {GROUP_ID}:{ARTIFACT_ID} "
#         f"from {current_version} to {latest_version}"
#     )


# def main():
#     print("=" * 70)
#     print("Nexus BOM Watcher")
#     print("=" * 70)

#     current_version = get_current_version()

#     print(f"Current POM version : {current_version}")

#     metadata = get_nexus_metadata()
#     latest_version = get_latest_version(metadata)

#     print(f"Latest Nexus version: {latest_version}")

#     if version_key(latest_version) <= version_key(current_version):
#         print(
#             f"No update required. "
#             f"Nexus={latest_version}, "
#             f"POM={current_version}"
#         )
#         return

#     print(
#         f"New BOM version detected: "
#         f"{current_version} -> {latest_version}"
#     )

#     update_pom(current_version, latest_version)

#     print(
#         f"Updated {POM_FILE}: "
#         f"{current_version} -> {latest_version}"
#     )


# if __name__ == "__main__":
#     main()
