-- phpMyAdmin SQL Dump
-- version 4.2.10
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Generation Time: Jun 12, 2015 at 06:00 PM
-- Server version: 5.6.21-log
-- PHP Version: 5.4.34

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
  `flag` tinyint(4) NOT NULL,
  `zone_id` tinyint(4) NOT NULL,
  `lts` int(10) unsigned NOT NULL,
  `lat` double NOT NULL,
  `lng` double NOT NULL,
  `js` blob NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `cashdrawer`
--

CREATE TABLE IF NOT EXISTS `cashdrawer` (
`rid` int(11) NOT NULL,
  `flag` tinyint(3) unsigned NOT NULL,
  `sid` tinyint(4) NOT NULL,
  `uid` int(11) NOT NULL,
  `diff` int(11) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `js` text NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `clockin_hist`
--

CREATE TABLE IF NOT EXISTS `clockin_hist` (
`id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `in_ts` int(10) unsigned NOT NULL,
  `out_ts` int(10) unsigned NOT NULL,
  `memo` varchar(128) NOT NULL,
  `flag` int(10) unsigned NOT NULL,
  `user_lvl` int(10) unsigned NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=5672 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `clockin_user`
--

CREATE TABLE IF NOT EXISTS `clockin_user` (
  `user_id` int(11) NOT NULL,
  `user_code` int(11) NOT NULL,
  `in_ts` int(10) unsigned NOT NULL,
  `rev` int(11) NOT NULL,
  `flag` int(10) unsigned NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `config`
--

CREATE TABLE IF NOT EXISTS `config` (
  `cid` int(11) NOT NULL,
  `cval` int(11) unsigned NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `configv2`
--

CREATE TABLE IF NOT EXISTS `configv2` (
  `ckey` varchar(256) NOT NULL,
  `cval` blob NOT NULL
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
  `note` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `customer_comment`
--

CREATE TABLE IF NOT EXISTS `customer_comment` (
`id` int(11) NOT NULL,
  `cid` bigint(11) NOT NULL,
  `js` blob NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=47 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `customer_delivery`
--

CREATE TABLE IF NOT EXISTS `customer_delivery` (
`cid` bigint(20) NOT NULL,
  `schedule` bigint(10) NOT NULL,
  `note` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `daily_inventory`
--

CREATE TABLE IF NOT EXISTS `daily_inventory` (
  `di_ts` int(10) unsigned NOT NULL,
  `di_price` float NOT NULL,
  `di_cost` float NOT NULL,
  `di_js` mediumblob NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `delivery`
--

CREATE TABLE IF NOT EXISTS `delivery` (
`id` int(11) NOT NULL,
  `rev` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `count` int(11) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `mts` int(10) unsigned NOT NULL,
  `name` varchar(128) NOT NULL,
  `js` text NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=55 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `deliveryv2`
--

CREATE TABLE IF NOT EXISTS `deliveryv2` (
`d_id` int(11) NOT NULL,
  `rev` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `count` int(11) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `mts` int(10) unsigned NOT NULL,
  `name` varchar(256) NOT NULL,
  `js` blob NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=1741 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `deliveryv2_receipt`
--

CREATE TABLE IF NOT EXISTS `deliveryv2_receipt` (
  `d_id` int(11) NOT NULL,
  `num` int(11) NOT NULL,
  `d_excluded` tinyint(4) NOT NULL,
  `sc_id` int(11) NOT NULL,
  `driver_id` int(11) NOT NULL,
  `delivered` tinyint(4) NOT NULL,
  `user_id` int(11) NOT NULL,
  `payment_required` tinyint(4) NOT NULL,
  `problem_flag` int(11) NOT NULL,
  `problem_flag_s` int(11) NOT NULL,
  `js` blob NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `doc_note`
--

CREATE TABLE IF NOT EXISTS `doc_note` (
`dn_id` int(11) NOT NULL,
  `dn_ts` int(10) unsigned NOT NULL,
  `doc_type` tinyint(4) NOT NULL,
  `doc_sid` bigint(11) NOT NULL,
  `dn_flag` int(11) unsigned NOT NULL,
  `dn_uid` int(11) NOT NULL,
  `dn_val` text NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=34022 DEFAULT CHARSET=utf8;

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
  `inv_total` float NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `invoicev2`
--

CREATE TABLE IF NOT EXISTS `invoicev2` (
  `inv_num` int(11) NOT NULL,
  `inv_date` int(11) NOT NULL,
  `inv_js` blob NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `inv_request`
--

CREATE TABLE IF NOT EXISTS `inv_request` (
`pid` int(11) NOT NULL,
  `rev` int(11) NOT NULL,
  `dst` tinyint(4) NOT NULL,
  `dtype` tinyint(4) NOT NULL,
  `flg` int(10) unsigned NOT NULL,
  `ref` bigint(11) DEFAULT NULL,
  `qbpos_id` int(11) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `uid` int(11) NOT NULL,
  `pdesc` varchar(256) NOT NULL,
  `pjs` blob NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=112 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `ipmac`
--

CREATE TABLE IF NOT EXISTS `ipmac` (
  `ip` tinyint(3) unsigned NOT NULL,
  `uts` int(10) unsigned NOT NULL,
  `mac` varchar(6) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `item`
--

CREATE TABLE IF NOT EXISTS `item` (
`sid` bigint(20) NOT NULL,
  `rev` int(11) NOT NULL DEFAULT '0',
  `inv_flag` int(10) unsigned NOT NULL DEFAULT '0',
  `imgs` blob
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `item_chg_hist`
--

CREATE TABLE IF NOT EXISTS `item_chg_hist` (
`ch_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `js` blob NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `msg`
--

CREATE TABLE IF NOT EXISTS `msg` (
`msg_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `msg_type` tinyint(4) NOT NULL,
  `msg_val` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `phycount_record`
--

CREATE TABLE IF NOT EXISTS `phycount_record` (
`r_id` int(11) NOT NULL,
  `r_rev` int(11) NOT NULL,
  `r_enable` tinyint(4) NOT NULL,
  `r_desc` varchar(256) NOT NULL,
  `r_loc` varchar(256) NOT NULL,
  `r_js` blob,
  `r_ts` int(10) unsigned NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=15 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `phycount_user`
--

CREATE TABLE IF NOT EXISTS `phycount_user` (
  `r_id` int(11) NOT NULL,
  `u_uid` int(11) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `phycount_user_hist`
--

CREATE TABLE IF NOT EXISTS `phycount_user_hist` (
`h_id` int(11) NOT NULL,
  `r_id` int(11) NOT NULL,
  `u_id` int(11) NOT NULL,
  `h_sid` bigint(20) NOT NULL,
  `h_qty` int(11) NOT NULL,
  `h_uom` varchar(16) NOT NULL,
  `h_loc` varchar(16) NOT NULL,
  `h_ts` int(10) unsigned NOT NULL,
  `h_js` blob
) ENGINE=MyISAM AUTO_INCREMENT=61 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `project`
--

CREATE TABLE IF NOT EXISTS `project` (
`p_id` int(11) NOT NULL,
  `p_prio` tinyint(4) NOT NULL,
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
  `p_msg` blob NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=16 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `qbcustomers`
--

CREATE TABLE IF NOT EXISTS `qbcustomers` (
  `cid` int(11) NOT NULL,
  `balance` float NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `qbdocs`
--

CREATE TABLE IF NOT EXISTS `qbdocs` (
  `tid` int(11) NOT NULL,
  `dtype` tinyint(4) NOT NULL,
  `customer_id` int(11) NOT NULL,
  `num` varchar(32) NOT NULL,
  `amt` float NOT NULL,
  `bal_amt` float NOT NULL,
  `doc_ts` int(10) unsigned NOT NULL,
  `is_paid` tinyint(4) NOT NULL,
  `doc_due` int(10) unsigned NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `qblinks`
--

CREATE TABLE IF NOT EXISTS `qblinks` (
  `sid` bigint(20) NOT NULL,
  `tid` int(11) NOT NULL,
  `doc_id` int(11) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `qbpos`
--

CREATE TABLE IF NOT EXISTS `qbpos` (
`id` int(11) NOT NULL,
  `rev` int(11) NOT NULL,
  `state` tinyint(4) NOT NULL,
  `errno` tinyint(11) NOT NULL,
  `doc_type` tinyint(4) NOT NULL,
  `doc_id` int(11) NOT NULL,
  `doc_sid` bigint(20) DEFAULT NULL,
  `doc_num` int(11) NOT NULL,
  `js` blob
) ENGINE=MyISAM AUTO_INCREMENT=75 DEFAULT CHARSET=utf8;

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
  `js` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `receipt_comment`
--

CREATE TABLE IF NOT EXISTS `receipt_comment` (
`rc_id` int(11) NOT NULL,
  `sid` bigint(20) NOT NULL,
  `sid_type` tinyint(4) NOT NULL,
  `ts` int(11) NOT NULL,
  `flag` int(11) NOT NULL,
  `name` varchar(128) NOT NULL,
  `comment` varchar(256) NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=15464 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `report`
--

CREATE TABLE IF NOT EXISTS `report` (
`id` int(11) NOT NULL,
  `type` tinyint(4) NOT NULL,
  `nz` varchar(128) NOT NULL,
  `js` blob NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=81 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `salesorder`
--

CREATE TABLE IF NOT EXISTS `salesorder` (
  `sid` bigint(20) NOT NULL,
  `delivery_date` int(11) NOT NULL,
  `delivery_zip` int(11) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `schedule`
--

CREATE TABLE IF NOT EXISTS `schedule` (
`sc_id` int(11) NOT NULL,
  `sc_date` int(10) unsigned NOT NULL,
  `sc_new_date` int(10) unsigned NOT NULL,
  `sc_rev` int(11) NOT NULL,
  `sc_flag` int(11) unsigned NOT NULL,
  `sc_prio` tinyint(4) NOT NULL,
  `doc_type` tinyint(4) NOT NULL,
  `doc_sid` bigint(20) NOT NULL,
  `doc_crc` int(10) unsigned DEFAULT NULL,
  `sc_note` varchar(256) NOT NULL,
  `doc_ijs_crc` int(10) unsigned DEFAULT NULL,
  `doc_ijs` blob,
  `doc_cur_ijs` blob
) ENGINE=MyISAM AUTO_INCREMENT=7673 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `schedule_special`
--

CREATE TABLE IF NOT EXISTS `schedule_special` (
  `ss_date` int(10) NOT NULL,
  `ss_zidx` tinyint(4) NOT NULL,
  `ss_val` tinyint(4) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sorder`
--

CREATE TABLE IF NOT EXISTS `sorder` (
`ord_id` int(11) NOT NULL,
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
  `ord_comment_js` text NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=810307 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_chg`
--

CREATE TABLE IF NOT EXISTS `sync_chg` (
`c_id` int(11) NOT NULL,
  `c_type` tinyint(4) NOT NULL,
  `c_js` blob NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=379619 DEFAULT CHARSET=utf8;

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
  `flag` int(11) unsigned NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_customer_chg`
--

CREATE TABLE IF NOT EXISTS `sync_customer_chg` (
`id` int(11) NOT NULL,
  `sid` bigint(20) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `js` blob NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=269 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_customer_snapshots`
--

CREATE TABLE IF NOT EXISTS `sync_customer_snapshots` (
  `sid` bigint(20) NOT NULL,
  `ts` int(10) unsigned NOT NULL,
  `js` blob NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_feed`
--

CREATE TABLE IF NOT EXISTS `sync_feed` (
`f_id` int(11) NOT NULL,
  `f_type` int(11) NOT NULL,
  `f_val` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

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
  `detail2` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_items_hist`
--

CREATE TABLE IF NOT EXISTS `sync_items_hist` (
`sid` bigint(20) NOT NULL,
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
  `docdate` int(10) unsigned NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=3480237769752580 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_items_upcs`
--

CREATE TABLE IF NOT EXISTS `sync_items_upcs` (
  `sid` bigint(20) NOT NULL,
  `upc` bigint(20) NOT NULL,
  `default_uom_idx` int(11) NOT NULL
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
  `doc_info` varchar(128) NOT NULL
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
  `items_js` text NOT NULL
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
  `items_js` text NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `sync_receipts_customers`
--

CREATE TABLE IF NOT EXISTS `sync_receipts_customers` (
  `sid` bigint(20) NOT NULL,
  `name` varchar(512) NOT NULL,
  `lookup` varchar(512) NOT NULL,
  `detail` text NOT NULL
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
  `detail` text NOT NULL
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
  `items_js` text NOT NULL
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
  `items_js` text NOT NULL
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
  `out_ip` int(11) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `tracker`
--

CREATE TABLE IF NOT EXISTS `tracker` (
`id` int(11) NOT NULL,
  `state` tinyint(3) NOT NULL,
  `type` tinyint(4) NOT NULL,
  `sid` bigint(20) NOT NULL,
  `js` blob NOT NULL,
  `mts` int(10) unsigned NOT NULL
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `user`
--

CREATE TABLE IF NOT EXISTS `user` (
`user_id` int(11) NOT NULL,
  `user_name` varchar(64) NOT NULL,
  `user_passwd` varchar(32) NOT NULL,
  `user_lvl` int(11) unsigned NOT NULL,
  `user_msg_id` int(11) NOT NULL,
  `user_roles` int(10) unsigned NOT NULL,
  `user_perms` blob
) ENGINE=MyISAM AUTO_INCREMENT=149 DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `user_role`
--

CREATE TABLE IF NOT EXISTS `user_role` (
`role_id` int(11) NOT NULL,
  `role_perms` blob
) ENGINE=MyISAM AUTO_INCREMENT=31 DEFAULT CHARSET=utf8;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `address`
--
ALTER TABLE `address`
 ADD PRIMARY KEY (`loc`), ADD KEY `flag` (`flag`);

--
-- Indexes for table `cashdrawer`
--
ALTER TABLE `cashdrawer`
 ADD PRIMARY KEY (`rid`);

--
-- Indexes for table `clockin_hist`
--
ALTER TABLE `clockin_hist`
 ADD PRIMARY KEY (`id`), ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `clockin_user`
--
ALTER TABLE `clockin_user`
 ADD PRIMARY KEY (`user_id`), ADD UNIQUE KEY `user_code` (`user_code`);

--
-- Indexes for table `config`
--
ALTER TABLE `config`
 ADD PRIMARY KEY (`cid`);

--
-- Indexes for table `configv2`
--
ALTER TABLE `configv2`
 ADD UNIQUE KEY `ckey` (`ckey`);

--
-- Indexes for table `customer`
--
ALTER TABLE `customer`
 ADD PRIMARY KEY (`cid`);

--
-- Indexes for table `customer_comment`
--
ALTER TABLE `customer_comment`
 ADD PRIMARY KEY (`id`), ADD KEY `cid` (`cid`,`id`);

--
-- Indexes for table `customer_delivery`
--
ALTER TABLE `customer_delivery`
 ADD PRIMARY KEY (`cid`), ADD KEY `cid` (`cid`);

--
-- Indexes for table `daily_inventory`
--
ALTER TABLE `daily_inventory`
 ADD PRIMARY KEY (`di_ts`);

--
-- Indexes for table `delivery`
--
ALTER TABLE `delivery`
 ADD PRIMARY KEY (`id`);

--
-- Indexes for table `deliveryv2`
--
ALTER TABLE `deliveryv2`
 ADD PRIMARY KEY (`d_id`);

--
-- Indexes for table `deliveryv2_receipt`
--
ALTER TABLE `deliveryv2_receipt`
 ADD UNIQUE KEY `d_id` (`d_id`,`num`), ADD KEY `num` (`num`), ADD KEY `sc_id` (`sc_id`);

--
-- Indexes for table `doc_note`
--
ALTER TABLE `doc_note`
 ADD PRIMARY KEY (`dn_id`), ADD KEY `doc_type` (`doc_type`,`doc_sid`);

--
-- Indexes for table `invoice`
--
ALTER TABLE `invoice`
 ADD KEY `inv_num` (`inv_num`,`inv_date`);

--
-- Indexes for table `invoicev2`
--
ALTER TABLE `invoicev2`
 ADD PRIMARY KEY (`inv_num`);

--
-- Indexes for table `inv_request`
--
ALTER TABLE `inv_request`
 ADD PRIMARY KEY (`pid`);

--
-- Indexes for table `ipmac`
--
ALTER TABLE `ipmac`
 ADD PRIMARY KEY (`ip`);

--
-- Indexes for table `item`
--
ALTER TABLE `item`
 ADD PRIMARY KEY (`sid`);

--
-- Indexes for table `item_chg_hist`
--
ALTER TABLE `item_chg_hist`
 ADD PRIMARY KEY (`ch_id`);

--
-- Indexes for table `msg`
--
ALTER TABLE `msg`
 ADD PRIMARY KEY (`msg_id`), ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `phycount_record`
--
ALTER TABLE `phycount_record`
 ADD PRIMARY KEY (`r_id`);

--
-- Indexes for table `phycount_user`
--
ALTER TABLE `phycount_user`
 ADD PRIMARY KEY (`r_id`,`u_uid`), ADD KEY `u_uid` (`u_uid`);

--
-- Indexes for table `phycount_user_hist`
--
ALTER TABLE `phycount_user_hist`
 ADD PRIMARY KEY (`h_id`), ADD KEY `h_sid` (`h_sid`), ADD KEY `u_id` (`u_id`,`r_id`);

--
-- Indexes for table `project`
--
ALTER TABLE `project`
 ADD PRIMARY KEY (`p_id`);

--
-- Indexes for table `qbcustomers`
--
ALTER TABLE `qbcustomers`
 ADD PRIMARY KEY (`cid`);

--
-- Indexes for table `qbdocs`
--
ALTER TABLE `qbdocs`
 ADD PRIMARY KEY (`tid`,`dtype`), ADD KEY `customer_id` (`customer_id`);

--
-- Indexes for table `qblinks`
--
ALTER TABLE `qblinks`
 ADD PRIMARY KEY (`tid`,`doc_id`), ADD KEY `sid` (`sid`);

--
-- Indexes for table `qbpos`
--
ALTER TABLE `qbpos`
 ADD PRIMARY KEY (`id`), ADD KEY `state` (`state`);

--
-- Indexes for table `receipt`
--
ALTER TABLE `receipt`
 ADD PRIMARY KEY (`sid`,`sid_type`);

--
-- Indexes for table `receipt_comment`
--
ALTER TABLE `receipt_comment`
 ADD PRIMARY KEY (`rc_id`), ADD KEY `sid` (`sid`,`sid_type`);

--
-- Indexes for table `report`
--
ALTER TABLE `report`
 ADD PRIMARY KEY (`id`);

--
-- Indexes for table `salesorder`
--
ALTER TABLE `salesorder`
 ADD PRIMARY KEY (`sid`), ADD KEY `delivery_date` (`delivery_date`);

--
-- Indexes for table `schedule`
--
ALTER TABLE `schedule`
 ADD PRIMARY KEY (`sc_id`), ADD UNIQUE KEY `doc_type` (`doc_type`,`doc_sid`,`sc_date`), ADD KEY `sc_date` (`sc_date`);

--
-- Indexes for table `schedule_special`
--
ALTER TABLE `schedule_special`
 ADD PRIMARY KEY (`ss_date`,`ss_zidx`);

--
-- Indexes for table `sorder`
--
ALTER TABLE `sorder`
 ADD PRIMARY KEY (`ord_id`);

--
-- Indexes for table `sync_chg`
--
ALTER TABLE `sync_chg`
 ADD PRIMARY KEY (`c_id`);

--
-- Indexes for table `sync_customers`
--
ALTER TABLE `sync_customers`
 ADD PRIMARY KEY (`sid`), ADD KEY `zip` (`zip`), ADD FULLTEXT KEY `name` (`name`,`lookup`);

--
-- Indexes for table `sync_customer_chg`
--
ALTER TABLE `sync_customer_chg`
 ADD PRIMARY KEY (`id`), ADD KEY `ts` (`ts`);

--
-- Indexes for table `sync_customer_snapshots`
--
ALTER TABLE `sync_customer_snapshots`
 ADD PRIMARY KEY (`sid`);

--
-- Indexes for table `sync_feed`
--
ALTER TABLE `sync_feed`
 ADD PRIMARY KEY (`f_id`);

--
-- Indexes for table `sync_items`
--
ALTER TABLE `sync_items`
 ADD PRIMARY KEY (`sid`), ADD KEY `deptsid` (`deptsid`), ADD KEY `status` (`status`), ADD FULLTEXT KEY `lookup` (`lookup`,`name`);

--
-- Indexes for table `sync_items_hist`
--
ALTER TABLE `sync_items_hist`
 ADD PRIMARY KEY (`sid`,`sid_type`), ADD KEY `itemsid` (`itemsid`), ADD KEY `docsid` (`docsid`,`sid_type`);

--
-- Indexes for table `sync_items_upcs`
--
ALTER TABLE `sync_items_upcs`
 ADD KEY `sid` (`sid`), ADD KEY `upc` (`upc`);

--
-- Indexes for table `sync_link_item`
--
ALTER TABLE `sync_link_item`
 ADD KEY `item_sid` (`item_sid`), ADD KEY `doc_sid` (`doc_sid`);

--
-- Indexes for table `sync_purchaseorders`
--
ALTER TABLE `sync_purchaseorders`
 ADD PRIMARY KEY (`sid`), ADD KEY `vend_sid` (`vend_sid`);

--
-- Indexes for table `sync_receipts`
--
ALTER TABLE `sync_receipts`
 ADD PRIMARY KEY (`sid`,`sid_type`), ADD KEY `cid` (`cid`), ADD KEY `num` (`num`), ADD KEY `so_sid` (`so_sid`);

--
-- Indexes for table `sync_receipts_customers`
--
ALTER TABLE `sync_receipts_customers`
 ADD PRIMARY KEY (`sid`), ADD FULLTEXT KEY `name` (`name`,`lookup`);

--
-- Indexes for table `sync_receipts_items`
--
ALTER TABLE `sync_receipts_items`
 ADD PRIMARY KEY (`sid`), ADD FULLTEXT KEY `lookup` (`lookup`,`name`);

--
-- Indexes for table `sync_salesorders`
--
ALTER TABLE `sync_salesorders`
 ADD PRIMARY KEY (`sid`), ADD KEY `cust_sid` (`cust_sid`), ADD KEY `sonum` (`sonum`);

--
-- Indexes for table `sync_vouchers`
--
ALTER TABLE `sync_vouchers`
 ADD PRIMARY KEY (`sid`), ADD KEY `vend_sid` (`vend_sid`,`ref_sid`);

--
-- Indexes for table `time`
--
ALTER TABLE `time`
 ADD KEY `user_id` (`user_id`,`in_ts`), ADD KEY `in_ts` (`in_ts`);

--
-- Indexes for table `tracker`
--
ALTER TABLE `tracker`
 ADD PRIMARY KEY (`id`), ADD KEY `sid` (`sid`), ADD KEY `type` (`type`);

--
-- Indexes for table `user`
--
ALTER TABLE `user`
 ADD PRIMARY KEY (`user_id`);

--
-- Indexes for table `user_role`
--
ALTER TABLE `user_role`
 ADD PRIMARY KEY (`role_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `cashdrawer`
--
ALTER TABLE `cashdrawer`
MODIFY `rid` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=5;
--
-- AUTO_INCREMENT for table `clockin_hist`
--
ALTER TABLE `clockin_hist`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=5672;
--
-- AUTO_INCREMENT for table `customer_comment`
--
ALTER TABLE `customer_comment`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=47;
--
-- AUTO_INCREMENT for table `customer_delivery`
--
ALTER TABLE `customer_delivery`
MODIFY `cid` bigint(20) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `delivery`
--
ALTER TABLE `delivery`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=55;
--
-- AUTO_INCREMENT for table `deliveryv2`
--
ALTER TABLE `deliveryv2`
MODIFY `d_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=1741;
--
-- AUTO_INCREMENT for table `doc_note`
--
ALTER TABLE `doc_note`
MODIFY `dn_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=34022;
--
-- AUTO_INCREMENT for table `inv_request`
--
ALTER TABLE `inv_request`
MODIFY `pid` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=112;
--
-- AUTO_INCREMENT for table `item`
--
ALTER TABLE `item`
MODIFY `sid` bigint(20) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `item_chg_hist`
--
ALTER TABLE `item_chg_hist`
MODIFY `ch_id` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `msg`
--
ALTER TABLE `msg`
MODIFY `msg_id` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `phycount_record`
--
ALTER TABLE `phycount_record`
MODIFY `r_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=15;
--
-- AUTO_INCREMENT for table `phycount_user_hist`
--
ALTER TABLE `phycount_user_hist`
MODIFY `h_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=61;
--
-- AUTO_INCREMENT for table `project`
--
ALTER TABLE `project`
MODIFY `p_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=16;
--
-- AUTO_INCREMENT for table `qbpos`
--
ALTER TABLE `qbpos`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=75;
--
-- AUTO_INCREMENT for table `receipt_comment`
--
ALTER TABLE `receipt_comment`
MODIFY `rc_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=15464;
--
-- AUTO_INCREMENT for table `report`
--
ALTER TABLE `report`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=81;
--
-- AUTO_INCREMENT for table `schedule`
--
ALTER TABLE `schedule`
MODIFY `sc_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=7673;
--
-- AUTO_INCREMENT for table `sorder`
--
ALTER TABLE `sorder`
MODIFY `ord_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=810307;
--
-- AUTO_INCREMENT for table `sync_chg`
--
ALTER TABLE `sync_chg`
MODIFY `c_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=379619;
--
-- AUTO_INCREMENT for table `sync_customer_chg`
--
ALTER TABLE `sync_customer_chg`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=269;
--
-- AUTO_INCREMENT for table `sync_feed`
--
ALTER TABLE `sync_feed`
MODIFY `f_id` int(11) NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `sync_items_hist`
--
ALTER TABLE `sync_items_hist`
MODIFY `sid` bigint(20) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=3480237769752580;
--
-- AUTO_INCREMENT for table `tracker`
--
ALTER TABLE `tracker`
MODIFY `id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=7;
--
-- AUTO_INCREMENT for table `user`
--
ALTER TABLE `user`
MODIFY `user_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=149;
--
-- AUTO_INCREMENT for table `user_role`
--
ALTER TABLE `user_role`
MODIFY `role_id` int(11) NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=31;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
