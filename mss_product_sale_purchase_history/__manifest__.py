# -*- coding: utf-8 -*-
#############################################################################################
#                                                                                           #
#    Maurya Software Solutions                                                              #
#    Copyright (C) 2018-TODAY Maurya Software Solutions(<http://www.maurysolutions.com>).   #
#    Author: Om Prakash Maurya(<https://www.maurysolutions.com>)                            #
#    you can modify it under the terms of the GNU LESSER                                    #
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.                                           #
#                                                                                           #
#    It is forbidden to publish, distribute, sublicense, or sell copies                     #
#    of the Software or modified copies of the Software.                                    #
#                                                                                           #
#    This program is distributed in the hope that it will be useful,                        #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of                         #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                          #
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.                          #
#                                                                                           #
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE               #
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.                              #
#    If not, see <http://www.gnu.org/licenses/>.                                            #
#                                                                                           #
#############################################################################################

{

    "name" : "Sale and Purchase History on Product",
    "version" : "1.0",
    'summary': 'Sale and Purchase History on Product Master',
    "description": """Showing total sales and purchases on product template and product product form view
    """,
    "author": "Maurya Software Solutions",
    'website': 'www.maurysolutions.com',
    'category': 'product',
    'depends': [
        'base',
        'product',
        'purchase',
        'sale',
        'stock',
        'purchase_discount',
        'mss_product_master'
    ],
    'data': [
        'views/product_sale_purchase_history_view.xml',
    ],
    'demo': [
    ],

    'images': ['static/description/product_history_banner.jpg'],
    "application":  True,
    "installable":  True,
    "auto_install":  False,
    'license': 'AGPL-3',
}


