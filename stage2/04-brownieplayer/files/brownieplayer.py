#!/usr/bin/env python3

import os
import stat
import subprocess
import re
import time
import shutil

usb_drive_paths = [
        '/dev/sda1',
        '/dev/sda',
]
usb_mount_point = '/mnt/usb'
filename_regexp = '^[^.].*\.(mp4|MP4|mov|MOV|avi|AVI|mpg|MPG)$'
omxplayer_args = ['--adev', 'both', '--blank', '--display', '7']
recommended_audio_codecs  = ['aac']
recommended_video_codec = 'h264'
local_playlist = '/home/pi/brownieplayer'

def main():
    print()
    print()
    line()
    log()
    log('http://www.brownieplayer.com/')
    line()
    log()
    log('Checking USB...')
    time.sleep(1)
    usb = get_usb_drive()
    playlist_dir = ""
    if usb != None:
        log('Found USB drive at %s.' % usb)
        if not os.path.exists(usb_mount_point):
            log('Creating mount point %s...' % usb_mount_point)
            os.mkdir(usb_mount_point)
        mount(usb, usb_mount_point)
        log('USB drive mounted at %s.' % usb_mount_point)
        playlist_dir = usb_mount_point
        if os.path.isfile(usb_mount_point + "/brownieplayer.py"):
            log("Found %s" % usb_mount_point + "/brownieplayer.py")
            exec(open(usb_mount_point + "/brownieplayer.py", "r").read())
            return
        if command(usb_mount_point, "clear"):
            log("Found command: clear")
            clear_local_playlist()
            return
        elif command(usb_mount_point, "copy"):
            log("Found command: copy")
            if os.path.exists(local_playlist):
                clear_local_playlist()
            else:
                os.mkdir(local_playlist)
            for f in get_media_files(playlist_dir):
                log("Copying %s..." % f)
                shutil.copyfile(f, local_playlist + "/" + os.path.basename(f))
            umount(usb_mount_point)
            log('Using playlist on SD card (%s).' % local_playlist)
            playlist_dir = local_playlist
    else:
        log('No USB drive found.')
        if os.path.isdir(local_playlist):
            log('Using playlist on SD card (%s).' % local_playlist)
            playlist_dir = local_playlist
        else:
            display_help()
            return

    media_files = get_media_files(playlist_dir)

    if len(media_files) == 0:
        log('No media files found.', Color.ERROR)
        display_help()
        return
    
    line()
    log()
    log('Found %i media file(s):' % len(media_files))

    has_warnings = False
    i = 1
    for f in media_files:
        log()
        log(str(i) + ". " + os.path.basename(f))
        i += 1
        try:
            probe_data = probe(f)
        except:
            log('   Error: Unable to decode file. Playback will probably fail.', Color.ERROR)
            has_warnings = True
            continue
        log('   Container: %s (%s)' % (probe_data['FORMAT'][0]['format_name'], probe_data['FORMAT'][0]['format_long_name']))
        has_warnings = check_streams(probe_data['STREAM'])

    line()

    wait_time = 15 if has_warnings else 5
    log()
    log('Proceeding in %s seconds...' % wait_time);

    time.sleep(wait_time)

    clear_tty()

    if len(media_files) == 1:
        play_loop(media_files[0])
    else:
        while True:
            for f in media_files:
                play(f)

def get_usb_drive():
    for p in usb_drive_paths:
        if is_blk(p):
            return p
    return None

def is_blk(path):
    if not os.path.exists(path):
            return False
    return stat.S_ISBLK(os.stat(path).st_mode)

def mount(drive, path):
    run_cmd(['mount', '-o', 'ro', drive, path])

def umount(path):
    if os.path.ismount(path):
        log("Unmounting %s..." % path)
        run_cmd(['umount', path])

def command(path, cmd):
    return os.path.isfile(path + "/brownieplayer." + cmd) or os.path.isfile(path + "/brownieplayer." + cmd + '.txt')

def clear_local_playlist():
    if os.path.exists(local_playlist):
        log("Clearing playlist on SD card...")
        for f in os.listdir(local_playlist):
            os.unlink(local_playlist + "/" + f)

def get_media_files(path):
    files = os.listdir(path)
    files = filter(lambda f: re.match(filename_regexp, f), files)
    files = sorted(files)
    files = map(lambda f: path + '/' + f, files)
    return list(files)

def probe(path):
    output, err = run_cmd(['ffprobe', '-v', 'error', '-show_format', '-show_streams', path])
    sections = {}
    section_current = None
    section_name = None
    for l in output.decode('utf-8').splitlines():
        tag = re.match('^\[(/?)(.*)\]$', l)
        if tag != None:
            if tag.group(1) == '':
                # start tag ([FORMAT], [STREAM], ...)
                context = tag.group(2)
                section_current = {}
                continue
            else:
                # end tag ([/FORMAT], ...)
                if context not in sections:
                        sections[context] = []
                sections[context].append(section_current)
                continue
        # key value pair
        fields = l.split('=')
        section_current[fields[0]] = fields[1]

    return sections

def check_streams(streams):
    has_warnings = False
    for s in streams:
        if s['codec_type'] == 'audio':
            log('   Audio: %s, %s Hz, %s, %s Channel(s)' % (s['codec_name'], s['sample_rate'], s['sample_fmt'], s['channels']))
            if not s['codec_name'] in recommended_audio_codecs:
                log('   Warning: %s is not a recommended audio codec. Playback might fail.' % s['codec_name'], Color.ERROR) 
                log('   Please use one of these instead: %s' % (", ".join(recommended_audio_codecs)), Color.ERROR)
                has_warnings = True
        elif s['codec_type'] == 'video':
            log('   Video: %s, %sx%s px, %s fps' % (s['codec_name'], s['width'], s['height'], s['avg_frame_rate']))
            if s['codec_name'] != recommended_video_codec:
                log('   Warning: %s is not a recommended video codec. Playback might fail.' % s['codec_name'], Color.ERROR)
                log('   Please use %s instead.' % (recommended_video_codec), Color.ERROR)
                has_warnings = True
    return has_warnings


def clear_tty():
    os.system('TERM=linux setterm -foreground black -clear all > /dev/tty0');

def play(path):
    cmd = ['omxplayer'] + omxplayer_args + [path]
    run_cmd(cmd)

def play_loop(path):
    cmd = ['omxplayer', '--loop'] + omxplayer_args + [path]
    log("Running: %s" % " ".join(cmd))
    run_cmd(cmd)

def display_help():
    line()
    log('')
    log('Please insert a USB drive that contains the media files in its root folder.')
    log('')
    log('Ensure that the following requirements are met:')
    log('')
    log('Supported file systems for USB drive: exFAT, FAT32, NTFS, EXT2, EXT3, EXT4')
    log('Supported video codec: H.264')
    log('Supported audio codecs: MP3, AAC')
    log('Maximum video resolution: 1920x1080 px (Full HD)')
    log('Supported container formats: MP4 (.mp4), QuickTime (.mov)')
    log('')
    log('Reboot to try again.')
    line()

def line():
    log('________________________________________________________________________________', Color.BROWN)

class Color:
    BROWN = '\x1b[0;33m'
    OK = '\x1b[0;32m'
    WARNING = '\x1b[0;31m'
    ERROR = '\x1b[0;31m'

def log(line='', color='\x1b[0m'):
    print(Color.BROWN + 'BrowniePlayer: ' + color + line + '\x1b[0m')

def run_cmd(cmd, env = []):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = p.communicate()
    if p.returncode != 0:
        raise Exception("\n" + cmd[0] + " returned:\nSTDOUT: " + output.decode('utf-8') + "\nSTDERR: " + err.decode('utf-8'))
    return (output, err)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log("Error: " + str(e), Color.ERROR)
    umount(usb_mount_point)
    log('')
    log("Exiting")
    line()

