# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-

# This file is part of Guadalinex
#
# This software is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this package; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

__author__ = "Antonio Hernández <ahernandez@emergya.com>"
__copyright__ = "Copyright (C) 2011, Junta de Andalucía <devmaster@guadalinex.org>"
__license__ = "GPL-2"


import LinkToChefHostnamePage
import LinkToChefResultsPage
import firstboot.pages.linkToChef
from firstboot.pages.network import interface
from firstboot_lib import PageWindow
from firstboot import serverconf
import firstboot.validation as validation

from gi.repository import Gtk
import requests
import hashlib
import gettext
from gettext import gettext as _
gettext.textdomain('gecosws-config-assistant')

__REQUIRED__ = False

__STATUS_TEST_PASSED__ = 0
__STATUS_CONFIG_CHANGED__ = 1
__STATUS_CONNECTING__ = 2
__STATUS_ERROR__ = 3


def get_page(main_window):

    page = LinkToChefConfEditorPage(main_window)
    return page


class LinkToChefConfEditorPage(PageWindow.PageWindow):
    __gtype_name__ = "LinkToChefConfEditorPage"

    def finish_initializing(self):
        self.show_status()

    def load_page(self, params=None):
        #content = serverconf.get_json_content()
        self.serverconf = serverconf.get_server_conf(None)
        self.gcc_conf = self.serverconf.get_gcc_conf()
        self.chef_conf = self.serverconf.get_chef_conf()
        self.ui.txtUrlChef.set_text(self.gcc_conf.get_uri_gcc())
        self.ui.txtUser.set_text(self.gcc_conf.get_gcc_username())
        self.ui.txtPassword.set_text(self.gcc_conf.get_gcc_pwd_user())

    def translate(self):
        desc = _('These parameters are required in order to join a Control Center:')

        self.ui.lblDescription.set_text(desc)
        self.ui.lblUrlChefDesc.set_label(_('"Control Center URL": an existant URL in your server where GECOS Control Center is installed.'))
        self.ui.lblUsernameDesc.set_label(_('"Username": User with administrative privilees (This will not be workstation user)'))
        self.ui.lblUrlChef.set_label('Control Center URL')
        self.ui.lblUser.set_label(_('Control Center Username'))
        self.ui.lblPassword.set_label(_('Password'))
        self.ui.chkLink.set_label(_('Link to an existing workstation?'))


    def previous_page(self, load_page_callback):
        load_page_callback(firstboot.pages.linkToChef)

    def next_page(self, load_page_callback):
        self.gcc_conf.set_uri_gcc(self.ui.txtUrlChef.get_text())
        self.gcc_conf.set_gcc_username(self.ui.txtUser.get_text())
        self.gcc_conf.set_gcc_pwd_user(self.ui.txtPassword.get_text())
        if not self.ui.chkLink.get_active():
            self.gcc_conf.set_gcc_link(True)
            self.gcc_conf.set_run(True)
            self.interfaces = interface.localifs()
            self.interfaces.reverse()
            #if len(self.gcc_conf.get_ou_username()) >= 2:
            result = serverconf.select_ou(_('Select OU'), _('Select the OU to link into GCC Ui'),self.ui.txtUrlChef.get_text(),self.ui.txtUser.get_text(),self.ui.txtPassword.get_text())#, self.gcc_conf.get_ou_username()) 
            self.gcc_conf.set_selected_ou(result)
            #elif len(self.gcc_conf.get_ou_username()) == 1:
            #    self.gcc_conf.set_selected_ou(self.gcc_conf.get_ou_username()[0][0])
            for inter in self.interfaces:
                if not inter[1].startswith('127.0'):
                    break
            if not serverconf.json_is_cached():
                result = serverconf.url_chef(_('Url Chef Certificate Required'), _('You need to enter url with certificate file\n in protocol://domain/resource format'))
                try:
                    res = requests.get(result)
                    if not res.ok:
                        raise serverconf.LinkToChefException(_("Can not download pem file"))
                    if hasattr(res,'text'):
                        pem = res.text
                    else:
                        pem = res.content
                    self.chef_conf.set_pem(pem.encode('base64'))
                    self.chef_conf.set_url(self.gcc_conf.get_uri_gcc())
                    self.chef_conf.set_admin_name(self.gcc_conf.get_gcc_username())

                    #result = serverconf.entry_ou(_('Select OU'),_('Enter the correct OU to link into GCC Ui'))
                    result = ''
                    #if result:
                    self.gcc_conf.set_selected_ou(result)
                    #else:
                    #    raise serverconf.LinkToChefException(_("You need enter a OU"))
                except Exception as e:
                    self.show_status(__STATUS_ERROR__, e)

            mac = interface.getHwAddr(inter[0])
            node_name = hashlib.md5(mac.encode()).hexdigest()
            self.gcc_conf.set_gcc_nodename(node_name)
            self.chef_conf.set_node_name(node_name)
            self.chef_conf.set_chef_link(True)
            self.chef_conf.set_chef_link_existing(False)
            result, messages = self.validate_conf()
            load_page_callback(LinkToChefResultsPage, {
                'result': result,
                'messages': messages
             })
        else:
            result = None
            try:
                hostnames = serverconf.get_hostnames(self.gcc_conf.get_uri_gcc(), self.gcc_conf.get_gcc_username(), self.gcc_conf.get_gcc_pwd_user())
                result = serverconf.select_node(_('Select Workstation'), _('Select a workstation to link'), hostnames)
                if result == None:
                    raise serverconf.LinkToChefException(_("You need selected a workstation"))
                self.gcc_conf.set_run(False)
                self.chef_conf.set_node_name(result)
                self.gcc_conf.set_gcc_nodename(result)
                self.chef_conf.set_chef_link_existing(True)
                self.chef_conf.set_chef_link(True)

                if not serverconf.json_is_cached():
                    result = serverconf.url_chef(_('Url Chef Certificate Required'), _('You need to enter url with certificate file\n in protocol://domain/resource format'))
                    try:
                        res = requests.get(result)
                        if not res.ok:
                            raise serverconf.LinkToChefException(_("Can not download pem file"))
                        if hasattr(res,'text'):
                            pem = res.text
                        else:
                            pem = res.content
                        self.chef_conf.set_pem(pem.encode('base64'))
                        self.chef_conf.set_url(self.gcc_conf.get_uri_gcc())
                        self.chef_conf.set_admin_name(self.gcc_conf.get_gcc_username())

                        #result = serverconf.entry_ou(_('Select OU'),_('Enter the correct OU to link into GCC Ui'))
                        result = ''
                        #if result:
                        self.gcc_conf.set_selected_ou(result)
                        #else:
                        #    raise serverconf.LinkToChefException(_("You need enter a OU"))
                    except Exception as e:
                        self.show_status(__STATUS_ERROR__, e)

                result, messages = self.validate_conf()
                load_page_callback(LinkToChefResultsPage, {
                    'result': result,
                    'messages': messages
                 })
            except Exception as e:
                self.show_status(__STATUS_ERROR__, e)
            

    def validate_conf(self):

        valid = True
        messages = []

        if not self.serverconf.get_chef_conf().validate():
            valid = False
            messages.append({'type': 'error', 'message': _('Chef URL must be valid URL and need certificate')})

        if not self.serverconf.get_gcc_conf().validate():
            valid = False
            messages.append({'type': 'error', 'message': _('Some GCC attributes are incorrect or blank')})


        return valid, messages

    def show_status(self, status=None, exception=None):

        icon_size = Gtk.IconSize.BUTTON

        if status == None:
            self.ui.imgStatus.set_visible(False)
            self.ui.lblStatus.set_visible(False)

        elif status == __STATUS_TEST_PASSED__:
            self.ui.imgStatus.set_from_stock(Gtk.STOCK_APPLY, icon_size)
            self.ui.imgStatus.set_visible(True)
            self.ui.lblStatus.set_label(_('The configuration file is valid.'))
            self.ui.lblStatus.set_visible(True)

        elif status == __STATUS_CONFIG_CHANGED__:
            self.ui.imgStatus.set_from_stock(Gtk.STOCK_APPLY, icon_size)
            self.ui.imgStatus.set_visible(True)
            self.ui.lblStatus.set_label(_('The configuration was updated successfully.'))
            self.ui.lblStatus.set_visible(True)

        elif status == __STATUS_ERROR__:
            self.ui.imgStatus.set_from_stock(Gtk.STOCK_DIALOG_ERROR, icon_size)
            self.ui.imgStatus.set_visible(True)
            self.ui.lblStatus.set_label(str(exception))
            self.ui.lblStatus.set_visible(True)

        elif status == __STATUS_CONNECTING__:
            self.ui.imgStatus.set_from_stock(Gtk.STOCK_CONNECT, icon_size)
            self.ui.imgStatus.set_visible(True)
            self.ui.lblStatus.set_label(_('Trying to connect...'))
            self.ui.lblStatus.set_visible(True)
