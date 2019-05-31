################################################################################
#      Copyright (C) 2015 Surfacingx                                           #
#                                                                              #
#  This Program is free software; you can redistribute it and/or modify        #
#  it under the terms of the GNU General Public License as published by        #
#  the Free Software Foundation; either version 2, or (at your option)         #
#  any later version.                                                          #
#                                                                              #
#  This Program is distributed in the hope that it will be useful,             #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of              #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                #
#  GNU General Public License for more details.                                #
#                                                                              #
#  You should have received a copy of the GNU General Public License           #
#  along with XBMC; see the file COPYING.  If not, write to                    #
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.       #
#  http://www.gnu.org/copyleft/gpl.html                                        #
################################################################################

import xbmc
import xbmcaddon
import xbmcvfs

import sys
import glob
import shutil
import re
import os

try:  # Python 3
    from urllib.parse import quote_plus
except ImportError:  # Python 2
    from urllib import quote_plus

from datetime import datetime

from resources.libs.config import CONFIG
from resources.libs import db
from resources.libs import downloader
from resources.libs import extract
from resources.libs import gui
from resources.libs import logging
from resources.libs import tools

if CONFIG.KODIV > 17:
    from resources.libs import zfile as zipfile
else:
    import zipfile


def cleanup_backup():
    folder = glob.glob(os.path.join(CONFIG.MYBUILDS, "*"))
    list = []
    filelist = []

    if len(folder) == 0:
        logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                           "[COLOR {0}]Backup Location: Empty[/COLOR]".format(CONFIG.COLOR2))
        return
    for item in sorted(folder, key=os.path.getmtime):
        filelist.append(item)
        base = item.replace(CONFIG.MYBUILDS, '')
        if os.path.isdir(item):
            list.append('/%s/' % base)
        elif os.path.isfile(item):
            list.append(base)
    list = ['--- Remove All Items ---'] + list
    selected = gui.DIALOG.select("{0}: Select the items to remove from the 'My_Builds' folder.".format(CONFIG.ADDONTITLE), list)

    if selected == -1:
        logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                           "[COLOR {0}]Clean Up Cancelled![/COLOR]".format(CONFIG.COLOR2))
    elif selected == 0:
        if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                            "[COLOR {0}]Would you like to clean up all items in your 'My_Builds' folder?[/COLOR]".format(CONFIG.COLOR2),
                            "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.MYBUILDS),
                            yeslabel="[B][COLOR springgreen]Clean Up[/COLOR][/B]",
                            nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
            clearedfiles, clearedfolders = tools.clean_house(CONFIG.MYBUILDS)
            logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                               "[COLOR {0}]Removed Files: [COLOR {1}]{2}[/COLOR] / Folders:[/COLOR] [COLOR {3}]{4}[/COLOR]".format(CONFIG.COLOR2, CONFIG.COLOR1, clearedfiles, CONFIG.COLOR1, clearedfolders))
        else:
            logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                               "[COLOR {0}]Clean Up Cancelled![/COLOR]".format(CONFIG.COLOR2))
    else:
        path = filelist[selected-1]
        passed = False

        if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                            "[COLOR {0}]Would you like to remove [COLOR {1}]{2}[/COLOR] from the 'My_Builds' folder?[/COLOR]".format(CONFIG.COLOR2, CONFIG.COLOR1, list[selected]),
                            "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, path),
                            yeslabel="[B][COLOR springgreen]Clean Up[/COLOR][/B]",
                            nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
            if os.path.isfile(path):
                try:
                    os.remove(path)
                    passed = True
                except:
                    logging.log("Unable to remove: {0}".format(path))
            else:
                tools.clean_house(path)
                try:
                    shutil.rmtree(path)
                    passed = True
                except Exception as e:
                    logging.log("Error removing {0}: {1}".format(path, e), level=xbmc.LOGNOTICE)
            if passed:
                logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                                   "[COLOR {0}]{1} Removed![/COLOR]".format(CONFIG.COLOR2, list[selected]))
            else:
                logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                                   "[COLOR {0}]Error Removing {1}![/COLOR]".format(CONFIG.COLOR2, list[selected]))
        else:
            logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                               "[COLOR {0}]Clean Up Cancelled![/COLOR]".format(CONFIG.COLOR2))


def addon_pack(name=""):
    if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                        "[COLOR {0}]Are you sure you wish to create an Addon Pack?[/COLOR]".format(CONFIG.COLOR2),
                        nolabel="[B][COLOR red]Cancel Backup[/COLOR][/B]",
                        yeslabel="[B][COLOR springgreen]Create Pack[/COLOR][/B]"):
        if name == "":
            name = tools.get_keyboard("", "Please enter a name for the add-on pack zip")
            if not name:
                return False
            name = quote_plus(name)
        name = '{0}.zip'.format(name)
        tempzipname = ''
        zipname = os.path.join(CONFIG.MYBUILDS, name)
        try:
            zipf = zipfile.ZipFile(xbmc.translatePath(zipname), mode='w')
        except:
            try:
                tempzipname = os.path.join(CONFIG.PACKAGES, '{0}.zip'.format(name))
                zipf = zipfile.ZipFile(tempzipname, mode='w')
            except:
                logging.log("Unable to create {0}.zip".format(name), level=xbmc.LOGERROR)
                if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                                    "[COLOR {0}]We are unable to write to the current backup directory, would you like to change the location?[/COLOR]".format(
                                        CONFIG.COLOR2),
                                    yeslabel="[B][COLOR springgreen]Change Directory[/COLOR][/B]",
                                    nolabel="[B][COLOR red]Cancel[/COLOR][/B]"):
                    CONFIG.open_settings()
                    return
                else:
                    return
        fold = glob.glob(os.path.join(CONFIG.ADDONS, '*/'))
        addonnames = []
        addonfolds = []
        for folder in sorted(fold, key=lambda x: x):
            foldername = os.path.split(folder[:-1])[1]
            if foldername in CONFIG.EXCLUDES:
                continue
            elif foldername in CONFIG.DEFAULTPLUGINS:
                continue
            elif foldername == 'packages':
                continue
            xml = os.path.join(folder, 'addon.xml')
            if os.path.exists(xml):
                match = tools.parse_dom(tools.read_from_file(xml), 'addon', ret='name')
                if len(match) > 0:
                    addonnames.append(match[0])
                    addonfolds.append(foldername)
                else:
                    addonnames.append(foldername)
                    addonfolds.append(foldername)

        selected = gui.DIALOG.multiselect(
            "{0}: Select the add-ons you wish to add to the zip.".format(CONFIG.ADDONTITLE, addonnames))
        if selected is None:
            selected = []

        logging.log(selected)
        gui.DP.create(CONFIG.ADDONTITLE,
                      '[COLOR {0}][B]Creating Zip File:[/B][/COLOR]'.format(CONFIG.COLOR2), '', 'Please Wait')
        if len(selected) > 0:
            added = []
            for item in selected:
                added.append(addonfolds[item])
                gui.DP.update(0, "", "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, addonfolds[item]))
                for base, dirs, files in os.walk(os.path.join(CONFIG.ADDONS, addonfolds[item])):
                    files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                    for file in files:
                        if file.endswith('.pyo'):
                            continue
                        gui.DP.update(0, "", "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, addonfolds[item]),
                                      "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, file))
                        fn = os.path.join(base, file)
                        zipf.write(fn, fn[len(CONFIG.ADDONS):], zipfile.ZIP_DEFLATED)
                dep = os.path.join(CONFIG.ADDONS, addonfolds[item], 'addon.xml')
                if os.path.exists(dep):
                    match = tools.parse_dom(tools.read_from_file(dep), 'import', ret='addon')
                    for depends in match:
                        if 'xbmc.python' in depends:
                            continue
                        if depends in added:
                            continue
                        gui.DP.update(0, "", "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, depends))
                        for base, dirs, files in os.walk(os.path.join(CONFIG.ADDONS, depends)):
                            files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                            for file in files:
                                if file.endswith('.pyo'):
                                    continue
                                gui.DP.update(0, "", "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, depends),
                                              "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, file))
                                fn = os.path.join(base, file)
                                zipf.write(fn, fn[len(CONFIG.ADDONS):], zipfile.ZIP_DEFLATED)
                                added.append(depends)
        gui.DIALOG.ok(CONFIG.ADDONTITLE,
                      "[COLOR {0}]{1}[/COLOR] [COLOR {2}]Backup successful:[/COLOR]".format(CONFIG.COLOR1, name,
                                                                                            CONFIG.COLOR2),
                      "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, zipname))


def build(name=""):
    if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                        "[COLOR {0}]Are you sure you wish to backup the current build?[/COLOR]".format(CONFIG.COLOR2),
                    nolabel="[B][COLOR red]Cancel Backup[/COLOR][/B]",
                    yeslabel="[B][COLOR springgreen]Backup Build[/COLOR][/B]"):
        if name == "":
            name = tools.get_keyboard("", "Please enter a name for the build zip")
            if not name:
                return False
            name = name.replace('\\', '').replace('/', '').replace(':', '').replace('*', '').replace('?', '').replace(
                '"', '').replace('<', '').replace('>', '').replace('|', '')
        name = quote_plus(name)
        tempzipname = ''
        zipname = os.path.join(CONFIG.MYBUILDS, '{0}.zip'.format(name))
        for_progress = 0
        ITEM = []
        exclude_data = False
        if not gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                                "[COLOR {0}]Do you want to include your addon_data folder?".format(CONFIG.COLOR2),
                                "This contains [COLOR {0}]ALL[/COLOR] add-on settings including passwords but may also contain important information such as skin shortcuts. We recommend [COLOR {0}]MANUALLY[/COLOR] removing the addon_data folders that aren\'t required.".format(CONFIG.COLOR1, CONFIG.COLOR1),
                                "[COLOR {0}]{1}[/COLOR] addon_data is ignored[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDON_ID),
                            yeslabel='[B][COLOR springgreen]Include data[/COLOR][/B]',
                            nolabel='[B][COLOR red]Don\'t Include[/COLOR][/B]'):
            exclude_data = True
        tools.convert_special(CONFIG.HOME, True)
        tools.ascii_check(CONFIG.HOME, True)
        extractsize = 0
        try:
            zipf = zipfile.ZipFile(xbmc.translatePath(zipname), mode='w')
        except:
            try:
                tempzipname = os.path.join(CONFIG.PACKAGES, '{0}.zip'.format(name))
                zipf = zipfile.ZipFile(tempzipname, mode='w')
            except:
                logging.log("Unable to create {0}.zip".format(name), level=xbmc.LOGERROR)
                if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                                "[COLOR {0}]We are unable to write to the current backup directory, would you like to change the location?[/COLOR]".format(CONFIG.COLOR2),
                                yeslabel="[B][COLOR springgreen]Change Directory[/COLOR][/B]",
                                nolabel="[B][COLOR red]Cancel[/COLOR][/B]"):
                    CONFIG.open_settings()
                    return
                else:
                    return
        gui.DP.create("[COLOR {0}]{1}[/COLOR][COLOR {2}]: Creating Zip[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                  "[COLOR {0}]Creating backup zip".format(CONFIG.COLOR2), "", "Please Wait...[/COLOR]")
        for base, dirs, files in os.walk(CONFIG.HOME):
            dirs[:] = [d for d in dirs if d not in CONFIG.EXCLUDE_DIRS]
            files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
            for file in files:
                ITEM.append(file)
        N_ITEM = len(ITEM)
        picture = []
        music = []
        video = []
        programs = []
        repos = []
        scripts = []
        skins = []
        fold = glob.glob(os.path.join(CONFIG.ADDONS, '*/'))
        idlist = []
        for folder in sorted(fold, key=lambda x: x):
            foldername = os.path.split(folder[:-1])[1]
            if foldername == 'packages':
                continue
            xml = os.path.join(folder, 'addon.xml')
            if os.path.exists(xml):
                a = tools.read_from_file(xml)
                prov = re.compile("<provides>(.+?)</provides>").findall(a)
                match = tools.parse_dom(prov, 'addon', ret='id')

                addid = foldername if len(match) == 0 else match[0]
                if addid in idlist:
                    continue
                idlist.append(addid)
                try:
                    add = xbmcaddon.Addon(id=addid)
                    aname = add.getAddonInfo('name')
                    aname = aname.replace('[', '<').replace(']', '>')
                    aname = str(re.sub('<[^<]+?>', '', aname)).lstrip()
                except:
                    aname = foldername
                if len(prov) == 0:
                    if foldername.startswith('skin'):
                        skins.append(aname)
                    elif foldername.startswith('repo'):
                        repos.append(aname)
                    else:
                        scripts.append(aname)
                    continue
                if not (prov[0]).find('executable') == -1:
                    programs.append(aname)
                if not (prov[0]).find('video') == -1:
                    video.append(aname)
                if not (prov[0]).find('audio') == -1:
                    music.append(aname)
                if not (prov[0]).find('image') == -1:
                    picture.append(aname)
        db.fix_metas()

        for base, dirs, files in os.walk(CONFIG.HOME):
            dirs[:] = [d for d in dirs if d not in CONFIG.EXCLUDE_DIRS]
            files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
            for file in files:
                try:
                    for_progress += 1
                    progress = tools.percentage(for_progress, N_ITEM)
                    gui.DP.update(int(progress),
                              '[COLOR {0}]Creating backup zip: [COLOR {1}]{2}[/COLOR] / [COLOR {3}]{4}[/COLOR]'.format(
                              CONFIG.COLOR2, CONFIG.COLOR1, for_progress, CONFIG.COLOR1, N_ITEM),
                                  '[COLOR {0}]{1}[/COLOR]'.format(CONFIG.COLOR1, file), '')
                    fn = os.path.join(base, file)
                    if file in CONFIG.LOGFILES:
                        logging.log("[Back Up] Type = build: Ignore {0} - Log File".format(file), level=xbmc.LOGNOTICE)
                        continue
                    elif os.path.join(base, file) in CONFIG.EXCLUDE_FILES:
                        logging.log("[Back Up] Type = build: Ignore {0} - Excluded File".format(file), level=xbmc.LOGNOTICE)
                        continue
                    elif os.path.join('addons', 'packages') in fn:
                        logging.log("[Back Up] Type = build: Ignore {0} - Packages Folder".format(file), level=xbmc.LOGNOTICE)
                        continue
                    elif os.path.join(CONFIG.ADDONS, 'inputstream.adaptive') in fn:
                        logging.log("[Back Up] Type = build: Ignore {0} - Binary Add-on".format(file), levvel=xbmc.LOGNOTICE)
                        continue
                    elif file.endswith('.csv'):
                        logging.log("[Back Up] Type = build: Ignore {0} - CSV File".format(file), level=xbmc.LOGNOTICE)
                        continue
                    elif file.endswith('.pyo'):
                        continue
                    elif file.endswith('.db') and 'Database' in base:
                        temp = file.replace('.db', '')
                        temp = ''.join([i for i in temp if not i.isdigit()])
                        if temp in CONFIG.DB_FILES:
                            if not file == db.latest_db(temp):
                                logging.log("[Back Up] Type = build: Ignore {0} - DB File".format(file), level=xbmc.LOGNOTICE)
                                continue
                    try:
                        zipf.write(fn, fn[len(CONFIG.HOME):], zipfile.ZIP_DEFLATED)
                        extractsize += os.path.getsize(fn)
                    except Exception as e:
                        logging.log("[Back Up] Type = build: Unable to backup {0}".format(file), level=xbmc.LOGNOTICE)
                        logging.log("{0} / {1}".format(Exception, e))
                    if gui.DP.iscanceled():
                        gui.DP.close()
                        logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                                  "[COLOR {0}]Backup Cancelled[/COLOR]".format(CONFIG.COLOR2))
                        sys.exit()
                except Exception as e:
                    logging.log("[Back Up] Type = build: Unable to backup {0}".format(file), level=xbmc.LOGNOTICE)
                    logging.log("Build Backup Error: {0}".format(str(e)), level=xbmc.LOGNOTICE)
        if exclude_data:
            match = glob.glob(os.path.join(CONFIG.ADDON_DATA, 'skin.*', ''))
            for fold in match:
                fd = os.path.split(fold[:-1])[1]
                if not fd in ['skin.confluence', 'skin.re-touch', 'skin.estuary', 'skin.estouchy']:
                    for base, dirs, files in os.walk(os.path.join(CONFIG.ADDON_DATA, fold)):
                        files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                        for file in files:
                            fn = os.path.join(base, file)
                            zipf.write(fn, fn[len(CONFIG.HOME):], zipfile.ZIP_DEFLATED)
                            extractsize += os.path.getsize(fn)
                    xml = os.path.join(CONFIG.ADDONS, fd, 'addon.xml')
                    if os.path.exists(xml):
                        matchxml = tools.parse_dom(tools.read_from_file(xml), 'import', ret='addon')
                        if 'script.skinshortcuts' in matchxml:
                            for base, dirs, files in os.walk(os.path.join(CONFIG.ADDON_DATA, 'script.skinshortcuts')):
                                files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                                for file in files:
                                    fn = os.path.join(base, file)
                                    zipf.write(fn, fn[len(CONFIG.HOME):], zipfile.ZIP_DEFLATED)
                                    extractsize += os.path.getsize(fn)
        zipf.close()
        xbmc.sleep(500)
        gui.DP.close()

        backup('guifix', name)

        if not tempzipname == '':
            success = xbmcvfs.rename(tempzipname, zipname)
            if success == 0:
                xbmcvfs.copy(tempzipname, zipname)
                xbmcvfs.delete(tempzipname)

        info(name, extractsize, programs, video, music, picture, repos, scripts)

        gui.DIALOG.ok(CONFIG.ADDONTITLE,
                      "[COLOR {0}]{1}[/COLOR] [COLOR {2}]Backup successful:[/COLOR]".format(CONFIG.COLOR1, name, CONFIG.COLOR2),
                      "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, zipname))


def info(name, extractsize, programs, video, music, picture, repos, scripts):
    info = name.replace('.zip', '.txt')
    f = open(info, 'w')
    f.close()
    with open(info, 'a') as f:
        f.write('name="{0}"\n'.format(name))
        f.write('extracted="{0}"\n'.format(extractsize))
        f.write('zipsize="{0}"\n'.format(os.path.getsize(xbmc.translatePath(name))))
        f.write('skin="{0}"\n'.format(CONFIG.SKIN))
        f.write('created="{0}"\n'.format(tools.get_date(now=True)))
        f.write('programs="{0}"\n'.format(', '.join(programs)) if len(programs) > 0 else 'programs="none"\n')
        f.write('video="{0}"\n'.format(', '.join(video)) if len(video) > 0 else 'video="none"\n')
        f.write('music="{0}"\n'.format(', '.join(music)) if len(music) > 0 else 'music="none"\n')
        f.write('picture="{0}"\n'.format(', '.join(picture)) if len(picture) > 0 else 'picture="none"\n')
        f.write('repos="{0}"\n'.format(', '.join(repos)) if len(repos) > 0 else 'repos="none"\n')
        f.write('scripts="{0}"\n'.format(', '.join(scripts)) if len(scripts) > 0 else 'scripts="none"\n')


def guifix(name=""):
    if name == "":
        guiname = tools.get_keyboard("", "Please enter a name for the GUI Fix zip")
        if not guiname:
            return False
        tools.convert_special(CONFIG.USERDATA, True)
        tools.ascii_check(CONFIG.USERDATA, True)
    else:
        guiname = name
    guiname = quote_plus(guiname)
    tempguizipname = ''
    guizipname = os.path.join(CONFIG.MYBUILDS, '{0}_guisettings.zip'.format(guiname))
    if os.path.exists(CONFIG.GUISETTINGS):
        try:
            zipf = zipfile.ZipFile(guizipname, mode='w')
        except:
            try:
                tempguizipname = os.path.join(CONFIG.PACKAGES, '{0}_guisettings.zip'.format(guiname))
                zipf = zipfile.ZipFile(tempguizipname, mode='w')
            except:
                logging.log("Unable to create {0}_guisettings.zip".format(guiname), level=xbmc.LOGERROR)
                if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                                "[COLOR {0}]We are unable to write to the current backup directory, would you like to change the location?[/COLOR]".format(CONFIG.COLOR2),
                                yeslabel="[B][COLOR springgreen]Change Directory[/COLOR][/B]",
                                nolabel="[B][COLOR red]Cancel[/COLOR][/B]"):
                    CONFIG.open_settings()
                    return
                else:
                    return
        try:
            zipf.write(CONFIG.GUISETTINGS, 'guisettings.xml', zipfile.ZIP_DEFLATED)
            zipf.write(CONFIG.PROFILES, 'profiles.xml', zipfile.ZIP_DEFLATED)
            match = glob.glob(os.path.join(CONFIG.ADDON_DATA, 'skin.*', ''))
            for fold in match:
                fd = os.path.split(fold[:-1])[1]
                if fd not in ['skin.confluence', 'skin.re-touch', 'skin.estuary', 'skin.estouchy']:
                    if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                                    "[COLOR {0}]Would you like to add the following skin folder to the GUI Fix Zip File?[/COLOR]".format(CONFIG.COLOR2),
                                    "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, fd),
                                    yeslabel="[B][COLOR springgreen]Add Skin[/COLOR][/B]",
                                    nolabel="[B][COLOR red]Skip Skin[/COLOR][/B]"):
                        for base, dirs, files in os.walk(os.path.join(CONFIG.ADDON_DATA, fold)):
                            files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                            for file in files:
                                fn = os.path.join(base, file)
                                zipf.write(fn, fn[len(CONFIG.USERDATA):], zipfile.ZIP_DEFLATED)
                        xml = os.path.join(CONFIG.ADDONS, fd, 'addon.xml')
                        if os.path.exists(xml):
                            matchxml = tools.parse_dom(tools.read_from_file(xml), 'import', ret='addon')
                            if 'script.skinshortcuts' in matchxml:
                                for base, dirs, files in os.walk(os.path.join(CONFIG.ADDON_DATA, 'script.skinshortcuts')):
                                    files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                                    for file in files:
                                        fn = os.path.join(base, file)
                                        zipf.write(fn, fn[len(CONFIG.USERDATA):], zipfile.ZIP_DEFLATED)
                    else:
                        logging.log("[Back Up] Type = guifix: {0} ignored".format(fold), level=xbmc.LOGNOTICE)
        except Exception as e:
            logging.log("[Back Up] Type = guifix: {0}".format(e), level=xbmc.LOGNOTICE)
            pass
        zipf.close()
        if not tempguizipname == '':
            success = xbmcvfs.rename(tempguizipname, guizipname)
            if success == 0:
                xbmcvfs.copy(tempguizipname, guizipname)
                xbmcvfs.delete(tempguizipname)
    else:
        logging.log("[Back Up] Type = guifix: guisettings.xml not found", level=xbmc.LOGNOTICE)
    if name == "":
        gui.DIALOG.ok(CONFIG.ADDONTITLE, "[COLOR {0}]GUI Fix backup successful:[/COLOR]".format(CONFIG.COLOR2),
                  "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, guizipname))


def theme(name=""):
    if not gui.DIALOG.yesno('[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                        "[COLOR {0}]Would you like to create a theme backup?[/COLOR]".format(CONFIG.COLOR2),
                        yeslabel="[B][COLOR springgreen]Continue[/COLOR][/B]",
                        nolabel="[B][COLOR red]No Cancel[/COLOR][/B]"):
        logging.log_notify("Theme Backup", "Cancelled!")
        return False
    if name == "":
        themename = tools.get_keyboard("", "Please enter a name for the theme zip")
        if not themename:
            return False
    else:
        themename = name
    themename = quote_plus(themename)
    tempzipname = ''
    zipname = os.path.join(CONFIG.MYBUILDS, '{0}.zip'.format(themename))
    try:
        zipf = zipfile.ZipFile(xbmc.translatePath(zipname), mode='w')
    except:
        try:
            tempzipname = os.path.join(CONFIG.PACKAGES, '{0}.zip'.format(themename))
            zipf = zipfile.ZipFile(tempzipname, mode='w')
        except:
            logging.log("Unable to create {0}.zip".format(themename), level=xbmc.LOGERROR)
            if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                            "[COLOR {0}]We are unable to write to the current backup directory, would you like to change the location?[/COLOR]".format(CONFIG.COLOR2),
                            yeslabel="[B][COLOR springgreen]Change Directory[/COLOR][/B]",
                            nolabel="[B][COLOR red]Cancel[/COLOR][/B]"):
                CONFIG.open_settings()
                return
            else:
                return
    tools.convert_special(CONFIG.USERDATA, True)
    tools.ascii_check(CONFIG.USERDATA, True)
    try:
        if not CONFIG.SKIN == 'skin.confluence':
            skinfold = os.path.join(CONFIG.ADDONS, CONFIG.SKIN, 'media')
            match2 = glob.glob(os.path.join(skinfold, '*.xbt'))
            if len(match2) > 1:
                if gui.DIALOG.yesno('[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                                "[COLOR {0}]Would you like to go through the Texture Files for?[/COLOR]".format(CONFIG.COLOR2),
                                "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.SKIN),
                                yeslabel="[B][COLOR springgreen]Add Textures[/COLOR][/B]",
                                nolabel="[B][COLOR red]Skip Textures[/COLOR][/B]"):
                    for xbt in match2:
                        if gui.DIALOG.yesno(
                                '[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                                "[COLOR {0}]Would you like to add the Texture File [COLOR {1}]{2}[/COLOR]?".format(
                                CONFIG.COLOR1, CONFIG.COLOR2, xbt.replace(skinfold, "")[1:]),
                                "from [COLOR {0}]{1}[/COLOR][/COLOR]".format(CONFIG.COLOR1, CONFIG.SKIN),
                                yeslabel="[B][COLOR springgreen]Add Textures[/COLOR][/B]",
                                nolabel="[B][COLOR red]Skip Textures[/COLOR][/B]"):
                            fn = xbt
                            fn2 = fn.replace(CONFIG.HOME, "")
                            zipf.write(fn, fn2, zipfile.ZIP_DEFLATED)
            else:
                for xbt in match2:
                    if gui.DIALOG.yesno(
                            '[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                            "[COLOR {0}]Would you like to add the Texture File [COLOR {1}]{2}[/COLOR]?".format(
                            CONFIG.COLOR2, CONFIG.COLOR1, xbt.replace(skinfold, "")[1:]),
                            "from [COLOR {0}]{1}[/COLOR][/COLOR]".format(CONFIG.COLOR1, CONFIG.SKIN),
                            yeslabel="[B][COLOR springgreen]Add Textures[/COLOR][/B]",
                            nolabel="[B][COLOR red]Skip Textures[/COLOR][/B]"):
                        fn = xbt
                        fn2 = fn.replace(CONFIG.HOME, "")
                        zipf.write(fn, fn2, zipfile.ZIP_DEFLATED)
            ad_skin = os.path.join(CONFIG.ADDON_DATA, CONFIG.SKIN, 'settings.xml')
            if os.path.exists(ad_skin):
                if gui.DIALOG.yesno('[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                                "[COLOR {0}]Would you like to go add the [COLOR {1}]settings.xml[/COLOR] in [COLOR {2}]/addon_data/[/COLOR] for?".format(
                                CONFIG.COLOR2, CONFIG.COLOR1, CONFIG.COLOR1), "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.SKIN),
                                yeslabel="[B][COLOR springgreen]Add Settings[/COLOR][/B]",
                                nolabel="[B][COLOR red]Skip Settings[/COLOR][/B]"):
                    zipf.write(ad_skin, ad_skin.replace(CONFIG.HOME, ""), zipfile.ZIP_DEFLATED)
            match = tools.parse_dom(tools.read_from_file(os.path.join(CONFIG.SKIN, 'addon.xml')), 'import', ret='addon')
            if 'script.skinshortcuts' in match:
                if gui.DIALOG.yesno('[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                                "[COLOR {0}]Would you like to go add the [COLOR {1}]settings.xml[/COLOR] for [COLOR {2}]script.skinshortcuts[/COLOR]?".format(
                                CONFIG.COLOR2, CONFIG.COLOR1, CONFIG.COLOR1),
                                    yeslabel="[B][COLOR springgreen]Add Settings[/COLOR][/B]",
                                nolabel="[B][COLOR red]Skip Settings[/COLOR][/B]"):
                    for base, dirs, files in os.walk(os.path.join(CONFIG.ADDON_DATA, 'script.skinshortcuts')):
                        files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                        for file in files:
                            fn = os.path.join(base, file)
                            zipf.write(fn, fn[len(CONFIG.HOME):], zipfile.ZIP_DEFLATED)
        if gui.DIALOG.yesno('[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                        "[COLOR {0}]Would you like to include a [COLOR {1}]Backgrounds[/COLOR] folder?[/COLOR]".format(
                        CONFIG.COLOR2, CONFIG.COLOR1),
                            yeslabel="[B][COLOR springgreen]Yes Include[/COLOR][/B]",
                        nolabel="[B][COLOR red]No Continue[/COLOR][/B]"):
            fn = gui.DIALOG.browse(0, 'Select location of backgrounds', 'files', '', True, False, CONFIG.HOME, False)
            if not fn == CONFIG.HOME:
                for base, dirs, files in os.walk(fn):
                    dirs[:] = [d for d in dirs if d not in CONFIG.EXCLUDE_DIRS]
                    files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                    for file in files:
                        try:
                            fn2 = os.path.join(base, file)
                            zipf.write(fn2, fn2[len(CONFIG.HOME):], zipfile.ZIP_DEFLATED)
                        except Exception as e:
                            logging.log("[Back Up] Type = theme: Unable to backup {0}".format(file), level=xbmc.LOGNOTICE)
                            logging.log("Backup Error: {0}".format(str(e)), level=xbmc.LOGNOTICE)
            text = db.latest_db('Textures')
            if gui.DIALOG.yesno('[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                            "[COLOR {0}]Would you like to include the [COLOR {1}]{2}[/COLOR]?[/COLOR]".format(
                            CONFIG.COLOR2, CONFIG.COLOR1, text),
                                yeslabel="[B][COLOR springgreen]Yes Include[/COLOR][/B]",
                            nolabel="[B][COLOR red]No Continue[/COLOR][/B]"):
                zipf.write(os.path.join(CONFIG.DATABASE, text), '/userdata/Database/{0}'.format(text), zipfile.ZIP_DEFLATED)
        if gui.DIALOG.yesno('[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                        "[COLOR {0}]Would you like to include any addons?[/COLOR]".format(CONFIG.COLOR2),
                        yeslabel="[B][COLOR springgreen]Yes Include[/COLOR][/B]",
                        nolabel="[B][COLOR red]No Continue[/COLOR][/B]"):
            fold = glob.glob(os.path.join(CONFIG.ADDONS, '*/'))
            addonnames = []
            addonfolds = []
            for folder in sorted(fold, key=lambda x: x):
                foldername = os.path.split(folder[:-1])[1]
                if foldername in CONFIG.EXCLUDES:
                    continue
                elif foldername in CONFIG.DEFAULTPLUGINS:
                    continue
                elif foldername == 'packages':
                    continue
                xml = os.path.join(folder, 'addon.xml')
                if os.path.exists(xml):
                    match = tools.parse_dom(tools.read_from_file(xml), 'addon', ret='name')
                    if len(match) > 0:
                        addonnames.append(match[0])
                        addonfolds.append(foldername)
                    else:
                        addonnames.append(foldername)
                        addonfolds.append(foldername)
            selected = gui.DIALOG.multiselect("{0}: Select the add-ons you wish to add to the zip.".format(CONFIG.ADDONTITLE), addonnames)
            if selected is None:
                selected = []
            if len(selected) > 0:
                added = []
                for item in selected:
                    added.append(addonfolds[item])
                    for base, dirs, files in os.walk(os.path.join(CONFIG.ADDONS, addonfolds[item])):
                        files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                        for file in files:
                            if file.endswith('.pyo'):
                                continue
                            fn = os.path.join(base, file)
                            zipf.write(fn, fn[len(CONFIG.HOME):], zipfile.ZIP_DEFLATED)
                    dep = os.path.join(CONFIG.ADDONS, addonfolds[item], 'addon.xml')
                    if os.path.exists(dep):
                        match = tools.parse_dom(tools.read_from_file(dep), 'import', ret='addon')
                        for depends in match:
                            if 'xbmc.python' in depends:
                                continue
                            if depends in added:
                                continue
                            for base, dirs, files in os.walk(os.path.join(CONFIG.ADDONS, depends)):
                                files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
                                for file in files:
                                    if file.endswith('.pyo'):
                                        continue
                                    fn = os.path.join(base, file)
                                    zipf.write(fn, fn[len(CONFIG.HOME):], zipfile.ZIP_DEFLATED)
                                    added.append(depends)
        if gui.DIALOG.yesno('[COLOR {0}]{1}[/COLOR][COLOR {2}]: Theme Backup[/COLOR]'.format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                        "[COLOR {0}]Would you like to include the [COLOR {1}]guisettings.xml[/COLOR]?[/COLOR]".format(
                        CONFIG.COLOR2, CONFIG.COLOR1),
                            yeslabel="[B][COLOR springgreen]Yes Include[/COLOR][/B]",
                        nolabel="[B][COLOR red]No Continue[/COLOR][/B]"):
            zipf.write(CONFIG.GUISETTINGS, '/userdata/guisettings.xml', zipfile.ZIP_DEFLATED)
    except Exception as e:
        zipf.close()
        logging.log("[Back Up] Type = theme: {0}".format(str(e)), level=xbmc.LOGNOTICE)
        gui.DIALOG.ok(CONFIG.ADDONTITLE, "[COLOR {0}]{1}[/COLOR][COLOR {2}] theme zip failed:[/COLOR]".format(CONFIG.COLOR1, themename, CONFIG.COLOR2),
                  "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, str(e)))
        if not tempzipname == '':
            try:
                os.remove(xbmc.translatePath(tempzipname))
            except Exception as e:
                logging.log(str(e))
        else:
            try:
                os.remove(xbmc.translatePath(zipname))
            except Exception as e:
                logging.log(str(e))
        return
    zipf.close()
    if not tempzipname == '':
        success = xbmcvfs.rename(tempzipname, zipname)
        if success == 0:
            xbmcvfs.copy(tempzipname, zipname)
            xbmcvfs.delete(tempzipname)
    gui.DIALOG.ok(CONFIG.ADDONTITLE, "[COLOR {0}]{1}[/COLOR][COLOR {2}] theme zip successful:[/COLOR]".format(CONFIG.COLOR1, themename, CONFIG.COLOR2),
              "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, zipname))


def addon_data(name=""):
    if gui.DIALOG.yesno(CONFIG.ADDONTITLE, "[COLOR {0}]Are you sure you wish to backup the current addon_data?[/COLOR]".format(CONFIG.COLOR2),
                    nolabel="[B][COLOR red]Cancel Backup[/COLOR][/B]",
                    yeslabel="[B][COLOR springgreen]Backup Addon_Data[/COLOR][/B]"):
        if name == "":
            name = tools.get_keyboard("", "Please enter a name for the addon_data zip")
            if not name:
                return False
            name = quote_plus(name)
        name = '{0}_addondata.zip'.format(name)
        tempzipname = ''
        zipname = os.path.join(CONFIG.MYBUILDS, name)
        try:
            zipf = zipfile.ZipFile(xbmc.translatePath(zipname), mode='w')
        except:
            try:
                tempzipname = os.path.join(CONFIG.PACKAGES, '{0}.zip'.format(name))
                zipf = zipfile.ZipFile(tempzipname, mode='w')
            except:
                logging.log("Unable to create {0}_addondata.zip".format(name), level=xbmc.LOGERROR)
                if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                                "[COLOR {0}]We are unable to write to the current backup directory, would you like to change the location?[/COLOR]".format(CONFIG.COLOR2),
                                yeslabel="[B][COLOR springgreen]Change Directory[/COLOR][/B]",
                                nolabel="[B][COLOR red]Cancel[/COLOR][/B]"):
                    CONFIG.open_settings()
                    return
                else:
                    return
        for_progress = 0
        ITEM = []
        tools.convert_special(CONFIG.ADDON_DATA, True)
        tools.ascii_check(CONFIG.ADDON_DATA, True)
        gui.DP.create("[COLOR {0}]{1}[/COLOR][COLOR {2}]: Creating Zip[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE, CONFIG.COLOR2),
                  "[COLOR {0}]Creating back up zip".format(CONFIG.COLOR2), "", "Please Wait...[/COLOR]")
        for base, dirs, files in os.walk(CONFIG.ADDON_DATA):
            dirs[:] = [d for d in dirs if d not in CONFIG.EXCLUDE_DIRS]
            files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
            for file in files:
                ITEM.append(file)
        N_ITEM = len(ITEM)

        bad_files = [
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.placenta', 'cache.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.placenta', 'cache.meta.5.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.placenta', 'cache.providers.13.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.exodusredux', 'cache.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.exodusredux', 'cache.meta.5.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.exodusredux', 'cache.providers.13.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.overeasy', 'cache.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.overeasy', 'cache.meta.5.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.overeasy', 'cache.providers.13.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.yoda', 'cache.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.yoda', 'cache.meta.5.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.yoda', 'cache.providers.13.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.scrubsv2', 'cache.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.scrubsv2', 'cache.meta.5.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.scrubsv2', 'cache.providers.13.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.gaia', 'cache.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.gaia', 'meta.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.seren', 'cache.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'plugin.video.seren', 'torrentScrape.db')),
            (os.path.join(CONFIG.ADDON_DATA, 'script.module.simplecache', 'simplecache.db'))]

        for base, dirs, files in os.walk(CONFIG.ADDON_DATA):
            dirs[:] = [d for d in dirs if d not in CONFIG.EXCLUDE_DIRS]
            files[:] = [f for f in files if f not in CONFIG.EXCLUDE_FILES]
            for file in files:
                try:
                    for_progress += 1
                    progress = tools.percentage(for_progress, N_ITEM)
                    gui.DP.update(int(progress),
                              '[COLOR {0}]Creating back up zip: [COLOR{1}]{2}[/COLOR] / [COLOR{3}]{4}[/COLOR]'.format(
                              CONFIG.COLOR2, CONFIG.COLOR1, for_progress, CONFIG.COLOR1, N_ITEM),
                                  '[COLOR {0}]{1}[/COLOR]'.format(CONFIG.COLOR1, file),
                              '')
                    fn = os.path.join(base, file)
                    if file in CONFIG.LOGFILES:
                        logging.log("[Back Up] Type = addon_data: Ignore {0} - Log Files".format(file), level=xbmc.LOGNOTICE)
                        continue
                    elif os.path.join(base, file) in bad_files:
                        logging.log("[Back Up] Type = addon_data: Ignore {0} - Cache Files".format(file), level=xbmc.LOGNOTICE)
                        continue
                    elif os.path.join('addons', 'packages') in fn:
                        logging.log("[Back Up] Type = addon_data: Ignore {0} - Packages Folder".format(file), level=xbmc.LOGNOTICE)
                        continue
                    elif file.endswith('.csv'):
                        logging.log("[Back Up] Type = addon_data: Ignore {0} - CSV File".format(file), level=xbmc.LOGNOTICE)
                        continue
                    elif file.endswith('.db') and 'Database' in base:
                        temp = file.replace('.db', '')
                        temp = ''.join([i for i in temp if not i.isdigit()])
                        if temp in CONFIG.DB_FILES:
                            if not file == db.latest_db(temp):
                                logging.log("[Back Up] Type = addon_data: Ignore {0} - Database Files".format(file), level=xbmc.LOGNOTICE)
                                continue
                    try:
                        zipf.write(fn, fn[len(CONFIG.ADDON_DATA):], zipfile.ZIP_DEFLATED)
                    except Exception as e:
                        logging.log("[Back Up] Type = addon_data: Unable to backup {0}".format(file), level=xbmc.LOGNOTICE)
                        logging.log("Backup Error: {0}".format(str(e)), level=xbmc.LOGNOTICE)
                except Exception as e:
                    logging.log("[Back Up] Type = addon_data: Unable to backup {0}".format(file), level=xbmc.LOGNOTICE)
                    logging.log("Backup Error: {0}".format(str(e)), level=xbmc.LOGNOTICE)
        zipf.close()
        if not tempzipname == '':
            success = xbmcvfs.rename(tempzipname, zipname)
            if success == 0:
                xbmcvfs.copy(tempzipname, zipname)
                xbmcvfs.delete(tempzipname)
        gui.DP.close()
        gui.DIALOG.ok(CONFIG.ADDONTITLE, "[COLOR {0}]{1}[/COLOR] [COLOR {2}]backup successful:[/COLOR]".format(CONFIG.COLOR1, name, CONFIG.COLOR2),
                  "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, zipname))


def backup(type):
    try:
        if not os.path.exists(CONFIG.BACKUPLOCATION):
            xbmcvfs.mkdirs(CONFIG.BACKUPLOCATION)
        if not os.path.exists(CONFIG.MYBUILDS):
            xbmcvfs.mkdirs(CONFIG.MYBUILDS)
    except Exception as e:
        gui.DIALOG.ok(CONFIG.ADDONTITLE,
                      "[COLOR {0}]Error making Back Up directories:[/COLOR]".format(CONFIG.COLOR2),
                      "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, str(e)))
        return
    if type == "addon_pack":
        addon_pack()
    elif type == "build":
        build()
    elif type == "guifix":
        guifix()
    elif type == "theme":
        theme()
    elif type == "addon_data":
        addon_data()


def restore_local(type):
    try:
        if not os.path.exists(CONFIG.BACKUPLOCATION):
            xbmcvfs.mkdirs(CONFIG.BACKUPLOCATION)
        if not os.path.exists(CONFIG.MYBUILDS):
            xbmcvfs.mkdirs(CONFIG.MYBUILDS)
    except Exception as e:
        gui.DIALOG.ok(CONFIG.ADDONTITLE,
                      "[COLOR {0}]Error making Back Up directories:[/COLOR]".format(CONFIG.COLOR2),
                      "[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, str(e)))
        return
    file = gui.DIALOG.browse(1, '[COLOR {0}]Select the backup file you want to restore[/COLOR]'.format(CONFIG.COLOR2),
                             'files', '.zip', False, False, CONFIG.MYBUILDS)
    logging.log("[RESTORE BACKUP {0}] File: {1} ".format(type.upper(), file), level=xbmc.LOGNOTICE)
    if file == "" or not file.endswith('.zip'):
        logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                           "[COLOR {0}]Local Restore: Cancelled[/COLOR]".format(CONFIG.COLOR2))
        return
    gui.DP.create(CONFIG.ADDONTITLE, '[COLOR {0}]Installing Local Backup'.format(CONFIG.COLOR2), '', 'Please Wait[/COLOR]')
    if not os.path.exists(CONFIG.USERDATA):
        os.makedirs(CONFIG.USERDATA)
    if not os.path.exists(CONFIG.ADDON_DATA):
        os.makedirs(CONFIG.ADDON_DATA)
    if not os.path.exists(CONFIG.PACKAGES):
        os.makedirs(CONFIG.PACKAGES)
    if type == "gui":
        loc = CONFIG.USERDATA
    elif type == "addon_data":
        loc = CONFIG.ADDON_DATA
    else:
        loc = CONFIG.HOME
    logging.log("Restoring to {0}".format(loc), level=xbmc.LOGNOTICE)
    display = os.path.split(file)
    fn = display[1]
    try:
        zipfile.ZipFile(file,  'r')
    except:
        gui.DP.update(0, '[COLOR {0}]Unable to read zipfile from current location.'.format(CONFIG.COLOR2), 'Copying file to packages')
        pack = os.path.join(CONFIG.PACKAGES, fn)
        xbmcvfs.copy(file, pack)
        file = xbmc.translatePath(pack)
        gui.DP.update(0, '', 'Copying file to packages: Complete')
        zipfile.ZipFile(file, 'r')
    percent, errors, error = extract.all(file, loc, gui.DP)
    db.fix_metas()
    CONFIG.clear_setting('build')
    gui.DP.close()
    from resources.libs import skin
    skin.skin_to_default()
    skin.look_and_feel_data('save')
    if not file.find('packages') == -1:
        try:
            os.remove(file)
        except:
            pass
    if int(errors) >= 1:
        if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                            '[COLOR {0}][COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR2, CONFIG.COLOR1, fn),
                            'Completed: [COLOR {0}]{1}{2}[/COLOR] [Errors:[COLOR {3}]{4}[/COLOR]]'.format(CONFIG.COLOR1, percent, '%', CONFIG.COLOR1, errors),
                            'Would you like to view the errors?[/COLOR]',
                            nolabel='[B][COLOR red]No Thanks[/COLOR][/B]',
                            yeslabel='[B][COLOR springgreen]View Errors[/COLOR][/B]'):
            if isinstance(errors, unicode):
                error = error.encode('utf-8')
            gui.show_text_box(CONFIG.ADDONTITLE, error.replace('\t',''))
    CONFIG.set_setting('installed', 'true')
    CONFIG.set_setting('extract', str(percent))
    CONFIG.set_setting('errors', str(errors))

    if CONFIG.INSTALLMETHOD == 1:
        todo = 1
    elif CONFIG.INSTALLMETHOD == 2:
        todo = 0
    else:
        todo = gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                                "[COLOR {0}]Would you like to [COLOR {1}]Force close[/COLOR] kodi or [COLOR {2}]Reload Profile[/COLOR]?[/COLOR]".format(CONFIG.COLOR2, CONFIG.COLOR1, CONFIG.COLOR1),
                                yeslabel="[B][COLOR red]Reload Profile[/COLOR][/B]",
                                nolabel="[B][COLOR springgreen]Force Close[/COLOR][/B]")

    if todo == 1:
        tools.reload_fix()
    else:
        tools.kill_kodi(True)


def restore_external(type):
    source = gui.DIALOG.browse(1,
                               '[COLOR {0}]Select the backup file you want to restore[/COLOR]'.format(CONFIG.COLOR2),
                               'files', '.zip', False, False)
    if source == "" or not source.endswith('.zip'):
        logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                           "[COLOR {0}]External Restore: Cancelled[/COLOR]".format(CONFIG.COLOR2))
        return
    if not source.startswith('http'):
        logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                           "[COLOR {0}]External Restore: Invalid URL[/COLOR]".format(CONFIG.COLOR2))
        return
    try:
        from resources.libs import check
        work = check.check_url(source)
    except:
        logging.log_notify("[COLOR {0}]{1}[/COLOR]".format(CONFIG.COLOR1, CONFIG.ADDONTITLE),
                           "[COLOR {0}]External Restore: Error Valid URL[/COLOR]".format(CONFIG.COLOR2))
        logging.log("Not a working url, if source was local then use local restore option", level=xbmc.LOGNOTICE)
        logging.log("External Source: {0}".format(source), level=xbmc.LOGNOTICE)
        return
    logging.log("[RESTORE EXT BACKUP {0}] File: {1} ".format(type.upper(), source), level=xbmc.LOGNOTICE)
    zipit = os.path.split(source)
    zname = zipit[1]
    gui.DP.create(CONFIG.ADDONTITLE, '[COLOR {0}]Downloading Zip file'.format(CONFIG.COLOR2), '', 'Please Wait[/COLOR]')
    if type == "gui":
        loc = CONFIG.USERDATA
    elif type == "addon_data":
        loc = CONFIG.ADDON_DATA
    else:
        loc = CONFIG.HOME
    if not os.path.exists(CONFIG.USERDATA):
        os.makedirs(CONFIG.USERDATA)
    if not os.path.exists(CONFIG.ADDON_DATA):
        os.makedirs(CONFIG.ADDON_DATA)
    if not os.path.exists(CONFIG.PACKAGES):
        os.makedirs(CONFIG.PACKAGES)
    file = os.path.join(CONFIG.PACKAGES, zname)
    downloader.download(source, file, gui.DP)
    gui.DP.update(0, 'Installing External Backup', '', 'Please Wait')
    percent, errors, error = extract.all(file, loc, gui.DP)
    db.fix_metas()
    CONFIG.clear_setting('build')
    gui.DP.close()
    from resources.libs import skin
    skin.skin_to_default()
    skin.look_and_feel_data('save')
    if int(errors) >= 1:
        if gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                            '[COLOR {0}][COLOR {1}]{2}[/COLOR]'.format(CONFIG.COLOR2, CONFIG.COLOR1, zname),
                            'Completed: [COLOR {0}]{1}{2}[/COLOR] [Errors:[COLOR {3}]{4}[/COLOR]]'.format(CONFIG.COLOR1, percent, '%', CONFIG.COLOR1, errors),
                            'Would you like to view the errors?[/COLOR]',
                            nolabel='[B][COLOR red]No Thanks[/COLOR][/B]',
                            yeslabel='[B][COLOR springgreen]View Errors[/COLOR][/B]'):
            gui.show_text_box(CONFIG.ADDONTITLE, error.replace('\t',''))
    CONFIG.set_setting('installed', 'true')
    CONFIG.set_setting('extract', str(percent))
    CONFIG.set_setting('errors', str(errors))
    try:
        os.remove(file)
    except:
        pass

    if CONFIG.INSTALLMETHOD == 1:
        todo = 1
    elif CONFIG.INSTALLMETHOD == 2:
        todo = 0
    else:
        todo = gui.DIALOG.yesno(CONFIG.ADDONTITLE,
                                "[COLOR {0}]Would you like to [COLOR {1}]Force close[/COLOR] kodi or [COLOR {2}]Reload Profile[/COLOR]?[/COLOR]".format(CONFIG.COLOR2, CONFIG.COLOR1, CONFIG.COLOR1),
                                yeslabel="[B][COLOR red]Reload Profile[/COLOR][/B]",
                                nolabel="[B][COLOR springgreen]Force Close[/COLOR][/B]")

    if todo == 1:
        tools.reload_fix()
    else:
        tools.kill_kodi(True)


# MIGRATION: move to backup
def restoreit(type):
    if type == 'build':
        x = freshStart('restore')
        if x == False: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]Local Restore Cancelled[/COLOR]" % COLOR2); return
    if not wiz.currSkin() in ['skin.confluence', 'skin.estuary']:
        wiz.skinToDefault('Restore Backup')
    wiz.restoreLocal(type)

# MIGRATION: move to backup
def restoreextit(type):
    if type == 'build':
        x = freshStart('restore')
        if x == False: wiz.LogNotify("[COLOR %s]%s[/COLOR]" % (COLOR1, ADDONTITLE), "[COLOR %s]External Restore Cancelled[/COLOR]" % COLOR2); return
    wiz.restoreExternal(type)