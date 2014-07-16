-- phpMyAdmin SQL Dump
-- version 4.0.7
-- http://www.phpmyadmin.net
--
-- Host: 127.0.0.1
-- Generation Time: Jul 15, 2014 at 05:47 PM
-- Server version: 5.6.14
-- PHP Version: 5.4.21

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;

--
-- Database: `posx`
--

-- --------------------------------------------------------

--
-- Table structure for table `address`
--

CREATE TABLE IF NOT EXISTS `address` (
  `loc` binary(20) NOT NULL,
  `ready` tinyint(4) NOT NULL,
  `lts` int(10) unsigned NOT NULL,
  `lat` float NOT NULL,
  `lng` float NOT NULL,
  `js` blob NOT NULL,
  PRIMARY KEY (`loc`),
  KEY `ready` (`ready`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `cashdrawer`
--

CREATE TABLE IF NOT EXISTS `cashdrawer` (
  `rid` int(11) NOT NULL AUTO_INCREMENT,
  `flag` tinyint(3) unsigned NOT NULL,
  `sid` tinyint(4) NOT NULL,
  `uid` int(11) NOT NULL,
  `diff` int(11) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `js` text NOT NULL,
  PRIMARY KEY (`rid`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=8 ;

-- --------------------------------------------------------

--
-- Table structure for table `clockin_hist`
--

CREATE TABLE IF NOT EXISTS `clockin_hist` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `in_ts` int(10) unsigned NOT NULL,
  `out_ts` int(10) unsigned NOT NULL,
  `memo` varchar(128) NOT NULL,
  `flag` int(10) unsigned NOT NULL,
  `user_lvl` int(10) unsigned NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=3473 ;

-- --------------------------------------------------------

--
-- Table structure for table `clockin_user`
--

CREATE TABLE IF NOT EXISTS `clockin_user` (
  `user_id` int(11) NOT NULL,
  `user_code` int(11) NOT NULL,
  `in_ts` int(10) unsigned NOT NULL,
  `rev` int(11) NOT NULL,
  `flag` int(10) unsigned NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_code` (`user_code`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `config`
--

CREATE TABLE IF NOT EXISTS `config` (
  `cid` int(11) NOT NULL,
  `cval` int(11) unsigned NOT NULL,
  PRIMARY KEY (`cid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `configv2`
--

CREATE TABLE IF NOT EXISTS `configv2` (
  `ckey` varchar(256) NOT NULL,
  `cval` blob NOT NULL,
  UNIQUE KEY `ckey` (`ckey`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `customer`
--

CREATE TABLE IF NOT EXISTS `customer` (
  `cid` bigint(20) NOT NULL,
  `schedule_date` int(10) NOT NULL,
  `schedule_rule` varchar(32) NOT NULL,
  `schedule_next` int(11) NOT NULL,
  `note` text NOT NULL,
  PRIMARY KEY (`cid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `customer_comment`
--

CREATE TABLE IF NOT EXISTS `customer_comment` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cid` bigint(11) NOT NULL,
  `js` blob NOT NULL,
  PRIMARY KEY (`id`),
  KEY `cid` (`cid`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=20 ;

-- --------------------------------------------------------

--
-- Table structure for table `customer_delivery`
--

CREATE TABLE IF NOT EXISTS `customer_delivery` (
  `cid` bigint(20) NOT NULL AUTO_INCREMENT,
  `schedule` bigint(10) NOT NULL,
  `note` text NOT NULL,
  PRIMARY KEY (`cid`),
  KEY `cid` (`cid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `daily_inventory`
--

CREATE TABLE IF NOT EXISTS `daily_inventory` (
  `di_ts` int(10) unsigned NOT NULL,
  `di_price` float NOT NULL,
  `di_cost` float NOT NULL,
  `di_js` mediumblob NOT NULL,
  PRIMARY KEY (`di_ts`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `delivery`
--

CREATE TABLE IF NOT EXISTS `delivery` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `rev` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `count` int(11) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `mts` int(10) unsigned NOT NULL,
  `name` varchar(128) NOT NULL,
  `js` text NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=55 ;

-- --------------------------------------------------------

--
-- Table structure for table `deliveryv2`
--

CREATE TABLE IF NOT EXISTS `deliveryv2` (
  `d_id` int(11) NOT NULL AUTO_INCREMENT,
  `rev` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `count` int(11) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `mts` int(10) unsigned NOT NULL,
  `name` varchar(256) NOT NULL,
  `js` blob NOT NULL,
  PRIMARY KEY (`d_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=556 ;

-- --------------------------------------------------------

--
-- Table structure for table `deliveryv2_receipt`
--

CREATE TABLE IF NOT EXISTS `deliveryv2_receipt` (
  `d_id` int(11) NOT NULL,
  `num` int(11) NOT NULL,
  `driver_id` int(11) NOT NULL,
  `delivered` tinyint(4) NOT NULL,
  `user_id` int(11) NOT NULL,
  `payment_required` tinyint(4) NOT NULL,
  `problem_flag` int(11) NOT NULL,
  `problem_flag_s` int(11) NOT NULL,
  `js` blob NOT NULL,
  UNIQUE KEY `d_id` (`d_id`,`num`),
  KEY `num` (`num`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `invoice`
--

CREATE TABLE IF NOT EXISTS `invoice` (
  `inv_num` int(11) NOT NULL,
  `inv_date` int(11) NOT NULL,
  `inv_clerk` varchar(16) NOT NULL,
  `inv_flag` int(11) NOT NULL,
  `inv_qbdate` varchar(16) NOT NULL,
  `inv_qbnum` varchar(16) NOT NULL,
  `inv_total` float NOT NULL,
  KEY `inv_num` (`inv_num`,`inv_date`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `invoicev2`
--

CREATE TABLE IF NOT EXISTS `invoicev2` (
  `inv_num` int(11) NOT NULL,
  `inv_date` int(11) NOT NULL,
  `inv_js` blob NOT NULL,
  PRIMARY KEY (`inv_num`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `ipmac`
--

CREATE TABLE IF NOT EXISTS `ipmac` (
  `ip` tinyint(3) unsigned NOT NULL,
  `uts` int(10) unsigned NOT NULL,
  `mac` varchar(6) NOT NULL,
  PRIMARY KEY (`ip`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `item`
--

CREATE TABLE IF NOT EXISTS `item` (
  `sid` bigint(20) NOT NULL AUTO_INCREMENT,
  `rev` int(11) NOT NULL DEFAULT '0',
  `inv_flag` int(10) unsigned NOT NULL DEFAULT '0',
  `imgs` blob,
  PRIMARY KEY (`sid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

-- --------------------------------------------------------

--
-- Table structure for table `item_chg_hist`
--

CREATE TABLE IF NOT EXISTS `item_chg_hist` (
  `ch_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `js` blob NOT NULL,
  PRIMARY KEY (`ch_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=15 ;

-- --------------------------------------------------------

--
-- Table structure for table `item_qty_rec`
--

CREATE TABLE IF NOT EXISTS `item_qty_rec` (
  `sid` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `ts` int(11) NOT NULL,
  `pos_qty` int(11) NOT NULL,
  `user_qty` int(11) NOT NULL,
  `js` blob NOT NULL,
  PRIMARY KEY (`sid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `msg`
--

CREATE TABLE IF NOT EXISTS `msg` (
  `msg_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `msg_type` tinyint(4) NOT NULL,
  `msg_val` text NOT NULL,
  PRIMARY KEY (`msg_id`),
  KEY `user_id` (`user_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=3 ;

-- --------------------------------------------------------

--
-- Table structure for table `project`
--

CREATE TABLE IF NOT EXISTS `project` (
  `p_id` int(11) NOT NULL AUTO_INCREMENT,
  `p_class` tinyint(4) NOT NULL,
  `p_state` tinyint(4) unsigned NOT NULL,
  `p_progress` tinyint(4) NOT NULL,
  `p_created_by_uid` int(11) NOT NULL,
  `p_approved_by_uid` int(11) NOT NULL,
  `p_name` varchar(128) NOT NULL,
  `p_desc` varchar(512) NOT NULL,
  `p_deadline_ts` int(10) unsigned NOT NULL,
  `p_beginning_ts` int(10) unsigned NOT NULL,
  `p_completion_ts` int(10) unsigned NOT NULL,
  `p_js` blob NOT NULL,
  `p_msg` blob NOT NULL,
  PRIMARY KEY (`p_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=9 ;

-- --------------------------------------------------------

--
-- Table structure for table `receipt`
--

CREATE TABLE IF NOT EXISTS `receipt` (
  `sid` bigint(20) NOT NULL,
  `sid_type` tinyint(4) NOT NULL,
  `flag` int(10) unsigned NOT NULL,
  `num` int(11) NOT NULL,
  `delivery_id` int(11) NOT NULL,
  `driver_id` int(11) NOT NULL,
  `memo` varchar(256) NOT NULL,
  `js` text NOT NULL,
  PRIMARY KEY (`sid`,`sid_type`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `receipt_comment`
--

CREATE TABLE IF NOT EXISTS `receipt_comment` (
  `rc_id` int(11) NOT NULL AUTO_INCREMENT,
  `sid` bigint(20) NOT NULL,
  `sid_type` tinyint(4) NOT NULL,
  `ts` int(11) NOT NULL,
  `flag` int(11) NOT NULL,
  `name` varchar(128) NOT NULL,
  `comment` varchar(256) NOT NULL,
  PRIMARY KEY (`rc_id`),
  KEY `sid` (`sid`,`sid_type`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=10857 ;

-- --------------------------------------------------------

--
-- Table structure for table `report`
--

CREATE TABLE IF NOT EXISTS `report` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` tinyint(4) NOT NULL,
  `nz` varchar(128) NOT NULL,
  `js` blob NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=37 ;

-- --------------------------------------------------------

--
-- Table structure for table `salesorder`
--

CREATE TABLE IF NOT EXISTS `salesorder` (
  `sid` bigint(20) NOT NULL,
  `delivery_date` int(11) NOT NULL,
  `delivery_zip` int(11) NOT NULL,
  PRIMARY KEY (`sid`),
  KEY `delivery_date` (`delivery_date`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `schedule`
--

CREATE TABLE IF NOT EXISTS `schedule` (
  `sc_id` int(11) NOT NULL AUTO_INCREMENT,
  `sc_date` int(10) unsigned NOT NULL,
  `sc_rev` int(11) NOT NULL,
  `sc_flag` int(11) unsigned NOT NULL,
  `doc_type` tinyint(4) NOT NULL,
  `doc_sid` bigint(20) NOT NULL,
  `doc_zone` tinyint(4) NOT NULL,
  `sc_note` varchar(128) NOT NULL,
  PRIMARY KEY (`sc_id`),
  KEY `sc_date` (`sc_date`),
  KEY `doc_type` (`doc_type`,`doc_sid`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=4 ;

-- --------------------------------------------------------

--
-- Table structure for table `sorder`
--

CREATE TABLE IF NOT EXISTS `sorder` (
  `ord_id` int(11) NOT NULL AUTO_INCREMENT,
  `ord_ref_id` int(11) NOT NULL,
  `ord_flag` int(11) NOT NULL,
  `ord_assoc_id` int(11) NOT NULL,
  `ord_user_id` int(11) NOT NULL,
  `ord_price_level` int(11) NOT NULL,
  `ord_order_date` int(10) unsigned NOT NULL,
  `ord_creation_date` int(10) unsigned NOT NULL,
  `ord_paid_date` int(10) unsigned NOT NULL,
  `ord_rev` int(11) NOT NULL,
  `ord_global_js` text NOT NULL,
  `ord_items_js` text NOT NULL,
  `ord_comment_js` text NOT NULL,
  PRIMARY KEY (`ord_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=810307 ;

-- --------------------------------------------------------

--
-- Table structure for table `sync_chg`
--

CREATE TABLE IF NOT EXISTS `sync_chg` (
  `c_id` int(11) NOT NULL AUTO_INCREMENT,
  `c_type` tinyint(4) NOT NULL,
  `c_js` blob NOT NULL,
  PRIMARY KEY (`c_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=8 ;

-- --------------------------------------------------------

--
-- Table structure for table `sync_customers`
--

CREATE TABLE IF NOT EXISTS `sync_customers` (
  `sid` bigint(20) NOT NULL,
  `name` varchar(512) NOT NULL,
  `lookup` varchar(512) NOT NULL,
  `detail` text NOT NULL,
  `zip` int(11) NOT NULL,
  `flag` int(11) unsigned NOT NULL,
  PRIMARY KEY (`sid`),
  KEY `zip` (`zip`),
  FULLTEXT KEY `name` (`name`,`lookup`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_feed`
--

CREATE TABLE IF NOT EXISTS `sync_feed` (
  `f_id` int(11) NOT NULL AUTO_INCREMENT,
  `f_type` int(11) NOT NULL,
  `f_val` text NOT NULL,
  PRIMARY KEY (`f_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=22416 ;

-- --------------------------------------------------------

--
-- Table structure for table `sync_items`
--

CREATE TABLE IF NOT EXISTS `sync_items` (
  `sid` bigint(20) NOT NULL,
  `deptsid` bigint(20) DEFAULT NULL,
  `status` tinyint(4) NOT NULL,
  `num` int(11) NOT NULL,
  `lookup` varchar(512) NOT NULL,
  `name` varchar(512) NOT NULL,
  `detail` text NOT NULL,
  `detail2` text NOT NULL,
  PRIMARY KEY (`sid`),
  KEY `deptsid` (`deptsid`),
  KEY `status` (`status`),
  FULLTEXT KEY `lookup` (`lookup`,`name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_items_hist`
--

CREATE TABLE IF NOT EXISTS `sync_items_hist` (
  `sid` bigint(20) NOT NULL AUTO_INCREMENT,
  `sid_type` tinyint(4) NOT NULL,
  `itemsid` bigint(20) NOT NULL,
  `docsid` bigint(20) NOT NULL,
  `docnum` int(11) NOT NULL,
  `flag` int(10) unsigned NOT NULL,
  `doctxt` varchar(256) NOT NULL,
  `qtynew` float NOT NULL,
  `qtydiff` float NOT NULL,
  `costnew` float NOT NULL,
  `costdiff` float NOT NULL,
  `extprice` float NOT NULL,
  `docdate` int(10) unsigned NOT NULL,
  PRIMARY KEY (`sid`,`sid_type`),
  KEY `itemsid` (`itemsid`),
  KEY `docsid` (`docsid`,`sid_type`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=3480237769752580 ;

-- --------------------------------------------------------

--
-- Table structure for table `sync_items_upcs`
--

CREATE TABLE IF NOT EXISTS `sync_items_upcs` (
  `sid` bigint(20) NOT NULL,
  `upc` bigint(20) NOT NULL,
  `default_uom_idx` int(11) NOT NULL,
  KEY `sid` (`sid`),
  KEY `upc` (`upc`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_link_item`
--

CREATE TABLE IF NOT EXISTS `sync_link_item` (
  `item_sid` bigint(20) NOT NULL,
  `doc_sid` bigint(20) NOT NULL,
  `doc_type` tinyint(4) NOT NULL,
  `flag` int(11) NOT NULL,
  `qty_ttl` int(11) NOT NULL,
  `qty_cur` int(11) NOT NULL,
  `doc_info` varchar(128) NOT NULL,
  KEY `item_sid` (`item_sid`),
  KEY `doc_sid` (`doc_sid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_purchaseorders`
--

CREATE TABLE IF NOT EXISTS `sync_purchaseorders` (
  `sid` bigint(20) NOT NULL,
  `vend_sid` bigint(20) NOT NULL,
  `status` int(11) NOT NULL,
  `ponum` varchar(32) NOT NULL,
  `clerk` varchar(64) NOT NULL,
  `podate` int(10) unsigned NOT NULL,
  `shipdate` int(10) unsigned NOT NULL,
  `duedate` int(10) unsigned NOT NULL,
  `creationdate` int(10) unsigned NOT NULL,
  `global_js` text NOT NULL,
  `items_js` text NOT NULL,
  PRIMARY KEY (`sid`),
  KEY `vend_sid` (`vend_sid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_receipts`
--

CREATE TABLE IF NOT EXISTS `sync_receipts` (
  `sid` bigint(20) NOT NULL,
  `sid_type` tinyint(4) NOT NULL,
  `rid` bigint(20) DEFAULT NULL,
  `cid` bigint(20) DEFAULT NULL,
  `so_sid` bigint(20) DEFAULT NULL,
  `so_type` int(11) NOT NULL,
  `type` int(10) unsigned NOT NULL,
  `num` int(11) NOT NULL,
  `assoc` varchar(64) NOT NULL,
  `cashier` varchar(64) NOT NULL,
  `price_level` int(11) NOT NULL,
  `order_date` int(10) unsigned NOT NULL,
  `creation_date` int(10) unsigned NOT NULL,
  `global_js` text NOT NULL,
  `items_js` text NOT NULL,
  PRIMARY KEY (`sid`,`sid_type`),
  KEY `cid` (`cid`),
  KEY `num` (`num`),
  KEY `so_sid` (`so_sid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_receipts_customers`
--

CREATE TABLE IF NOT EXISTS `sync_receipts_customers` (
  `sid` bigint(20) NOT NULL,
  `name` varchar(512) NOT NULL,
  `lookup` varchar(512) NOT NULL,
  `detail` text NOT NULL,
  PRIMARY KEY (`sid`),
  FULLTEXT KEY `name` (`name`,`lookup`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_receipts_items`
--

CREATE TABLE IF NOT EXISTS `sync_receipts_items` (
  `sid` bigint(20) NOT NULL,
  `num` int(11) NOT NULL,
  `lookup` varchar(512) NOT NULL,
  `name` varchar(512) NOT NULL,
  `detail` text NOT NULL,
  PRIMARY KEY (`sid`),
  FULLTEXT KEY `lookup` (`lookup`,`name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_salesorders`
--

CREATE TABLE IF NOT EXISTS `sync_salesorders` (
  `sid` bigint(20) NOT NULL,
  `cust_sid` bigint(20) DEFAULT NULL,
  `status` int(11) NOT NULL,
  `price_level` int(11) NOT NULL,
  `sonum` varchar(32) NOT NULL,
  `clerk` varchar(32) NOT NULL,
  `cashier` varchar(32) NOT NULL,
  `sodate` int(10) unsigned NOT NULL,
  `duedate` int(10) unsigned NOT NULL,
  `creationdate` int(10) unsigned NOT NULL,
  `global_js` text NOT NULL,
  `items_js` text NOT NULL,
  PRIMARY KEY (`sid`),
  KEY `cust_sid` (`cust_sid`),
  KEY `sonum` (`sonum`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_vouchers`
--

CREATE TABLE IF NOT EXISTS `sync_vouchers` (
  `sid` bigint(20) NOT NULL,
  `vend_sid` bigint(20) DEFAULT NULL,
  `ref_sid` bigint(20) DEFAULT NULL,
  `status` int(11) NOT NULL,
  `num` int(11) NOT NULL,
  `clerk` varchar(32) NOT NULL,
  `voucherdate` int(10) unsigned NOT NULL,
  `duedate` int(10) unsigned NOT NULL,
  `invdate` int(10) unsigned NOT NULL,
  `creationdate` int(10) unsigned NOT NULL,
  `global_js` text NOT NULL,
  `items_js` text NOT NULL,
  PRIMARY KEY (`sid`),
  KEY `vend_sid` (`vend_sid`,`ref_sid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `time`
--

CREATE TABLE IF NOT EXISTS `time` (
  `user_id` int(11) NOT NULL,
  `in_ts` int(11) NOT NULL,
  `out_ts` int(11) NOT NULL,
  `in_ip` int(11) NOT NULL,
  `out_ip` int(11) NOT NULL,
  KEY `user_id` (`user_id`,`in_ts`),
  KEY `in_ts` (`in_ts`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `user`
--

CREATE TABLE IF NOT EXISTS `user` (
  `user_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_name` varchar(64) NOT NULL,
  `user_passwd` varchar(32) NOT NULL,
  `user_lvl` int(11) unsigned NOT NULL,
  `user_msg_id` int(11) NOT NULL,
  PRIMARY KEY (`user_id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=145 ;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
