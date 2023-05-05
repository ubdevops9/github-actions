# !/usr/bin/python
# cleanup_images.py
#   - Get the images based on the icr.io/clickhouse/clickhouse and release.
#   - Calculates the current timestamp and the timestamp for oldest image, based on that checks SUPPORT_WINDOW.
#   - Get all the latest image based on the latest tag.
#   - Delete the images which does not have the latest tag.
#
# Parameters : 
#   release,            # any parameter can be passed based on release. ex: 23.1,23.2
#   release_custom,     # customizing the release value. ex: 23\.1,23\.2
#
from datetime import datetime
from os import getenv
import getopt
import os
import psycopg2
import subprocess
import sys
database_cert = os.environ.get('DBCERT')
db_user_password = os.environ.get('DBUSERPW')
 print(db_user_password)
 print(database_cert)

 param_dic = {
     "host"      : "bd634caa-1c30-4770-b25d-8b470642f5ea.c7dvrhud08vgdqo60090.databases.appdomain.cloud",
     "port"      : 32412,
     "database"  : "clickhouse_analysis",
     "user"      : "codechecker",
     "password"  : db_user_password,
     "sslrootcert" : database_cert
 }

 debug=True
 if debug:
  print("Printing debug info. To turn off, set debug=False one lines above this line in the code")
def get_filtered_images(release_custom, release):
    if debug:
      print(f"debug: function: get_filtered_images: {release} {release_custom}")
    # Filter the list of images that match the pattern
    image_list_output = subprocess.check_output(f'ibmcloud cr image-list | grep "icr.io/clickhouse/clickhouse" | grep -E "(clickhouse|clickhouse-openssl)" | grep -v "icr.io/clickhouse/clickhouse-operator" | grep "{release_custom}\.[0-9]"', shell=True)    
    filtered_images = image_list_output.decode('utf-8')
    filtered_images_list = filtered_images.strip().split('\n')
    filtered_images_list = [line.split() for line in filtered_images_list]
    print('filtered images for release', {release})
    for image in filtered_images_list:
        print(image)
    return filtered_images_list  
def oldest_tag_date(release):
    connection = psycopg2.connect(**param_dic)
    cursor = connection.cursor()
    oldest_tag_query = f"SELECT MIN(tag) as oldest_tag, MAX(tag) as newest_tag, MIN(release_date) AS oldest_date, MAX(release_date) AS newest_date FROM audit.releases WHERE branch = '{release}'"
    cursor.execute(oldest_tag_query)
    filter_tag_date = cursor.fetchone()
    oldest_tag = filter_tag_date[0]
    latest_tag = filter_tag_date[1]
    oldest_release_date = filter_tag_date[2]
    latest_release_date = filter_tag_date[3]
    print(f"Oldest_release_tag: {oldest_tag} released on {oldest_release_date}")
    print(f"latest_release_tag: {latest_tag} released on {latest_release_date}")
    print("Oldest tag:", oldest_tag)
    print("Newest tag:", latest_tag)
    print("Oldest date:", oldest_release_date)
    print("latest date:", latest_release_date)
    cursor.close()
    connection.close()
    return oldest_tag, oldest_release_date, latest_tag, latest_release_date
def calculate_timestamps_sec(oldest_release_date):
    oldest_date= datetime.strptime(oldest_release_date, '%Y-%m-%d')
    oldest_timestamp_sec = oldest_date.timestamp()
    print("Oldest timestamp in seconds: ",oldest_timestamp_sec)
    current_timestamp_sec = int(datetime.now().timestamp())
    print("Current timestamp in seconds: ",current_timestamp_sec)    
    return oldest_timestamp_sec, current_timestamp_sec
def determine_support_window(oldest_tag):
    if 'stable' in oldest_tag:
        print("Stable version, 3 months supports window") 
        # Set the time period for which packages will be kept (in seconds)
        SUPPORT_WINDOW = 90 * 24 * 60 * 60
        if debug:
            print("debug: SUPPORT WINDOW for stable releases ", SUPPORT_WINDOW)        
    else:
        print("lts version, 1 year supports window")
        # Set the time period for which packages will be kept (in seconds)
        SUPPORT_WINDOW = 365 * 24 * 60 * 60
        if debug:
            print("debug: SUPPORT WINDOW for LTS release ", SUPPORT_WINDOW)             
    return SUPPORT_WINDOW
def extract_version(latest_tag, SUPPORT_WINDOW):
    version = latest_tag[1:]  # remove the leading "v"
    if SUPPORT_WINDOW == 90:
        latest_version = version.replace("-stable", "")  # remove the trailing "-stable"
        if debug:
            print("debug: latest version :", latest_version)
    else:
        latest_version = version.replace("-lts", "")  # remove the trailing "-lts"
        if debug:
            print("debug: latest version :", latest_version)
    print('latest-version',latest_version)
    return latest_version
def get_latest_images(filtered_images_list, latest_version):
    latest_images = []
    for image in filtered_images_list:
        if latest_version in image[1]:
            latest_images.append(image)
    latest_images.sort(reverse=True)
    latest_image_tag = latest_images[0][1]
    print(latest_image_tag)
    latest_tag = latest_image_tag.split('-')[0] + "-" + latest_image_tag.split('-')[1]
    if debug:
        print("debug: latest tag for images :", latest_tag)    
    latest_tag_images = []
    for image in filtered_images_list:
        if latest_tag in image[1]:
            latest_tag_images.append(image)
    print('List of latest images that will not be deleted :')
    for images in latest_tag_images:
        print(images)    
    print('latest tag',latest_tag)
    return latest_tag
def delete_images(filtered_images_list, latest_tag, release):
    """
    Delete packages.
    """
    print('latest tag',latest_tag)
    with open(getenv('LATEST_TAG'), 'a') as latest:
        latest.write(latest_tag + '\n')
    image_tags = []
    for image in filtered_images_list:
        image_tags.append(image[1])
    tags_to_be_deleted = []
    for tag in image_tags:
        if latest_tag not in tag:
            tags_to_be_deleted.append(tag)
    print('tags_to_be_deleted:')
    for image in tags_to_be_deleted:
        print(image)
    # Deleting PACKAGES as it's not under support window
    for image_tag in tags_to_be_deleted:
        print('Delete', image_tag)
        
        # converting to float
        release_float = float(release)
        # checking if the release is >= 23.2
        if release_float >= 23.2:
            print("going to delete clickhouse and clickhouse-openssl images")
            # os.system(f"ibmcloud cr image-rm icr.io/clickhouse/clickhouse:{image_tag}")
            # os.system(f"ibmcloud cr image-rm icr.io/clickhouse/clickhouse-openssl:{image_tag}")
        else:
            print("going to delete clickhouse image")
            # os.system(f"ibmcloud cr image-rm icr.io/clickhouse/clickhouse:{image_tag}")            
    return tags_to_be_deleted
def main():
    # Default values for release_custom and release
    release = None
    release_custom = None    
    # Parsing command-line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:c:", ["help", "release=", "custom="])
    except getopt.GetoptError:
        print(f"Usage: {sys.argv[0]} -r <release> -c <release_custom>")
        sys.exit(1)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(f"Usage: {sys.argv[0]} -r <release> -c <release_custom>")
            sys.exit()
        elif opt in ("-r", "--release"):
            release = arg
        elif opt in ("-c", "--custom"):
            release_custom = arg
    if not release or not release_custom:
        print(f"Usage: {sys.argv[0]} --release <release> --custom <release_custom>")
        sys.exit(1)
    filtered_images_list = get_filtered_images(release_custom, release)
    oldest_tag, oldest_release_date, latest_tag, latest_release_date = oldest_tag_date(release)
    oldest_timestamp_sec, current_timestamp_sec = calculate_timestamps_sec(oldest_release_date)
    SUPPORT_WINDOW = determine_support_window(oldest_tag)
    print("Checking if it is under support window")
    if current_timestamp_sec - oldest_timestamp_sec > SUPPORT_WINDOW:
        print(f"Support period for release {release} has ended, Delete the packages")
        latest_version = extract_version(latest_tag, SUPPORT_WINDOW)
        latest_images = get_latest_images(filtered_images_list, latest_version)
        delete_images(filtered_images_list, latest_images, release)
if __name__ == "__main__":
    main()
