<?php

// Used parts from phpmailer library
// details on http://phpmailer.codeworxtech.com/

function send_mail($email, $subject, $message, $from, $mode)
{
	global $settings;

	$from_header_name = stripslashes($settings["GlobalSiteName"]);
	$from_header_email = $settings["GlobalNotificationEmail"];

	$eol_character = getMailHeaderEolCharacter();

	// if it is an array, we have a name and email address
	if (is_array($from))
	{
		if (!array_key_exists('email', $from) || !array_key_exists('name', $from))
			throw new Exception('Expecting keys "name" and "email"');

		$from_header_name = $from['name'];
		$from_header_email = $from['email'];

	}
	// if it is a string, this should only be an email address, mark name as blank
	else if (trim($from) != '')
	{
		$from_header_name = '';
		$from_header_email = $from;
	}


	if ($settings["EmailSendmailEngine"] == "mail")
	{
		$headers = "";
		if ($mode == "html") $headers .= "Content-type: text/html; charset=utf-8".$eol_character;

		// these are the headers we want to send
		$headers .= "From: \"".$from_header_name."\"<".$from_header_email.">".$eol_character;
		$headers .= "Reply-To: \"".$from_header_name."\"<".$from_header_email.">".$eol_character;
		$headers .= "Return-Path: ".$settings["GlobalNotificationEmail"].$eol_character;

		$mailResult = @mail($email, $subject, $message.$eol_character, $headers, "-f".$from_header_email);

		return $mailResult;
	}
	else
	{
		require_once("content/classes/class.phpmailer.php");
		require_once("content/classes/class.smtp.php");

		$mail = new PHPMailer();

		$mail->CharSet = 'utf-8';
		$mail->SetLanguage("en", "content/classes/");

		$mail->IsSMTP();

		$mail->SMTPSecure = $settings["EmailSMTPSecure"]; // sets the prefix to the servier
		$mail->Host = $settings["EmailSMTPServer"]; // sets GMAIL as the SMTP server
		$mail->Port = $settings["EmailSMTPPort"]; // set the SMTP port

		if($settings["EmailSMTPLogin"] != "" && $settings["EmailSMTPPassword"] != ""){
			$mail->SMTPAuth = true;                  // enable SMTP authentication
			$mail->Username = $settings["EmailSMTPLogin"];  // GMAIL username
			$mail->Password = $settings["EmailSMTPPassword"];            // GMAIL password
		}

		$from = is_array($from) ? $from["email"] : $from;

		$mail->From = $from_header_email;
		$mail->FromName = $from_header_name;
		$mail->Subject = $subject;
		$mail->Body = $message;

		$mail->Encoding = "base64";

		//$mail->AltBody    = "This is the body when user views in plain text format"; //Text Body
		//$mail->WordWrap   = 50; // set word wrap

		$mail->AddAddress($email, $email);
		$mail->AddReplyTo($from_header_email, $from_header_name);

		if ($mode == "html") $mail->IsHTML(true); // send as HTML

		if (!$mail->Send())
		{
			return false;
		}
		else
		{
			return true;
		}
	}
}

/**
 * Send email on new user registered
 * @param $db
 * @param $uid
 * @param $custom_fields
 */
function emailNewUserRegistered(&$db, $uid, &$customFields)
{
	global $settings;
	global $msg;
	$db->query("
		SELECT ".DB_PREFIX."users.*, ".DB_PREFIX."countries.name AS country_name
		FROM ".DB_PREFIX."users
		LEFT JOIN ".DB_PREFIX."countries ON ".DB_PREFIX."users.country = ".DB_PREFIX."countries.coid
		WHERE uid='".$uid."'
	");
	if ($db->moveNext())
	{
		$user_data = $db->col;

		$cf_billing = $customFields->getCustomFieldsValues("billing", $uid, 0, 0);
		$cf_account = $customFields->getCustomFieldsValues("account", $uid, 0, 0);
		$cf_signup = $customFields->getCustomFieldsValues("signup", $uid, 0, 0);

		view()->assign("user_data", $user_data);

		view()->assign("cf_billing", $cf_billing);
		view()->assign("cf_account", $cf_account);
		view()->assign("cf_signup", $cf_signup);

		view()->assign("EmailTitle", "Registration Details");

		$message_user = view()->fetch("templates/emails/signup_user_".$user_data["email_mode"].".html");
		$message_html = view()->fetch("templates/emails/signup_admin_html.html");
		$message_text = view()->fetch("templates/emails/signup_admin_text.html");

		if (!ini_get('safe_mode')) set_time_limit(300);

		//send email to user
		send_mail($user_data["email"], stripslashes($settings["CompanyName"].": ".$msg["email"]["subject_new_user_welcome"]), $message_user, "", $user_data["email_mode"]);

		//send to admins
		$db->query("SELECT * FROM ".DB_PREFIX."admins WHERE active='Yes' AND (rights LIKE '%users%' OR rights LIKE '%all%') AND (receive_notifications LIKE '%signup%')");
		while($db->moveNext()){
			header("Pong: ping");
			send_mail($db->col["email"], stripslashes($settings["CompanyName"].": ".$msg["email"]["subject_new_user_registered"]), $db->col["email_mode"]=="html"?$message_html:$message_text, "", $db->col["email_mode"]);
			header("Pind: pong");
		}
	}
}

/**
 * Send password reset email
 * @param $db
 * @param $uid
 * @param $new_password
 */
function emailUserResetPassword($user_data, $uid, $new_password){
	global $settings;
	global $msg;
	view()->assign("EmailTitle", "Your New Password");
	view()->assign("fname", $user_data["fname"]);
	view()->assign("lname", $user_data["lname"]);
	view()->assign("username", $user_data["login"]);
	view()->assign("password", $new_password);
	$message = view()->fetch("templates/emails/reset_password_".$user_data["email_mode"].".html");

	if (!ini_get('safe_mode')) set_time_limit(300);
	send_mail($user_data["email"], stripslashes($settings["CompanyName"].": ".$msg["email"]["subject_new_password"]), $message, "", $user_data["email_mode"]);
}

/**
 * Send out of stock email
 * @param $db
 * @param $pid
 * @param $new_stock
 * @param $inventory_id
 */
function emailOutOfStock(&$db, $pid, $new_stock, $inventory_id = 0){
	global $settings;
	global $msg;
	$db->query("SELECT * FROM ".DB_PREFIX."products WHERE pid='".$pid."'");
	if($db->moveNext()){
		$product = $db->col;
		$product_attributes_stock = false;
		if($inventory_id > 0){
			$db->query("SELECT * FROM ".DB_PREFIX."products_inventory WHERE pid='".$pid."' AND pi_id='".$inventory_id."'");
			if($db->moveNext()){
				$product_attributes_stock = $db->col;
			}
		}
		view()->assign("EmailTitle", "Product Out Of Stock: ".htmlspecialchars($product["title"].($product_attributes_stock?(" - ".str_replace("\n", ",", $product_attributes_stock["attributes_list"])):"")));
		view()->assign("product", $product);
		view()->assign("new_stock", $new_stock);
		view()->assign("product_attributes_stock", $product_attributes_stock);
		$message_html = view()->fetch("templates/emails/outofstock_admin_html.html");
		$message_text = view()->fetch("templates/emails/outofstock_admin_text.html");

		//send to admins
		$db->query("SELECT * FROM ".DB_PREFIX."admins WHERE active='Yes' AND (rights LIKE '%products%' OR rights LIKE '%all%') AND (receive_notifications LIKE '%outofstock%')");
		while($db->moveNext()){
			header("Pong: ping");
			send_mail($db->col["email"], stripslashes($settings["CompanyName"].": ".$msg["email"]["subject_out_of_stock"]." (".gs($product["title"]).")"), $db->col["email_mode"]=="html"?$message_html:$message_text, "", $db->col["email_mode"]);
			header("Pind: pong");
		}
	}
}

/**
 * Send order received email
 * @param $db
 * @param $order
 * @param $user
 * @param $customFields
 * @param $payment_status
 */
function emailOrderReceived(&$db, &$order, &$user, &$customFields, $payment_status)
{
	global $settings;
	global $msg;

	view()->assign("EmailTitle", "Order Details");

	$order->getOrderData();
	view()->assign("order", $order);

	$user_data = $user->getUserData();
	$order_items = $order->getOrderItems();
	$shipping_address = $order->getShippingAddress();

	view()->assign("user_data", $user_data);
	view()->assign("billing_address", $user_data);
	view()->assign("shipping_address", $shipping_address);
	view()->assign("order_items", $order_items);

	$payment = new PAYMENT($db, false);
	if ($payment->isMethod($order->paymentMethodId))
	{
		$pm = $payment->methods[$order->paymentMethodId];
		view()->assign("payment_method_thankyou", $pm->message_thankyou);
		if ($order->paymentIsRealtime == "Yes")
		{
			view()->assign("payment_realtime", "yes");
			view()->assign("payment_method_name", $pm->type." (".$pm->name.")");
		}
		else
		{
			view()->assign("payment_realtime", "no");
			view()->assign("payment_method_name", $pm->name);
		}
	}

	$cf_billing = $customFields->getCustomFieldsValues("billing", $user->id, 0, 0);
	$cf_shipping = $customFields->getCustomFieldsValues("shipping", $user->id, $order->oid, 0);
	$cf_invoice = $customFields->getCustomFieldsValues("invoice", $user->id, $order->oid, 0);

	view()->assign("cf_billing", $cf_billing);
	view()->assign("cf_shipping", $cf_shipping);
	view()->assign("cf_invoice", $cf_invoice);

	view()->assign("payment_status", $payment_status);

	$message_user = view()->fetch("templates/emails/order_received_user_".$user->data["email_mode"].".html");
	$message_html = view()->fetch("templates/emails/order_received_admin_html.html");
	$message_text = view()->fetch("templates/emails/order_received_admin_text.html");

	if (!ini_get('safe_mode')) set_time_limit(300);

	//send email to users
	//send_mail($user->data["email"], stripslashes($settings["CompanyName"].": ".$msg["email"]["subject_your_order"]." - ".$order->order_num), $message_user, "", $user->data["email_mode"]);
	send_mail("mark.richman@nutrihealth.com", stripslashes($settings["CompanyName"].": ".$msg["email"]["subject_your_order"]." - ".$order->order_num), $message_user, "", $user->data["email_mode"]);

	//send to admins
	$db->query("SELECT * FROM ".DB_PREFIX."admins WHERE active='Yes' AND (rights LIKE '%orders%' OR rights LIKE '%all%') AND (receive_notifications LIKE '%invoice%')");
	while ($db->moveNext())
	{
		header("Pong: ping");
		send_mail($db->col["email"], stripslashes($settings["CompanyName"].": ".$msg["email"]["subject_new_order"]." - ".$order->order_num), $db->col["email_mode"]=="html"?$message_html:$message_text, "", $db->col["email_mode"]);
		header("Pind: pong");
	}
}

/**
 * Send order completed email
 * @param $db
 * @param $oid
 */
function emailOrderCompleted(&$db, $oid){
	global $settings;
	global $msg;
	$db->query("
		SELECT
			".DB_PREFIX."orders.*,
			shipping_countries.name AS shipping_country_name
		FROM ".DB_PREFIX."orders
		LEFT JOIN ".DB_PREFIX."countries AS shipping_countries ON ".DB_PREFIX."orders.shipping_country = shipping_countries.coid
		WHERE oid='".intval($oid)."'"
	);
	if($db->moveNext()){
		$order_data = $db->col;
		$db->query("SELECT * FROM ".DB_PREFIX."orders_content WHERE oid='".intval($oid)."'");
		$order_items = $db->getRecords();

		for ($i=0; $i<count($order_items); $i++)
		{
			if ($order_items[$i]["product_sub_id"] != "")
			{
				$order_items[$i]["product_id"] = $order_items[$i]["product_id"]." / ".$order_items[$i]["product_sub_id"];
			}
		}

		if($settings["DisplayPricesWithTax"] == "YES"){
			$order_data["subtotal_amount"] = 0;
			for($i=0; $i<count($order_items); $i++){
				if($order_items[$i]["is_taxable"] == "Yes"){
					$order_items[$i]["admin_price"] = $order_items[$i]["admin_price"] + $order_items[$i]["admin_price"] / 100 *  $order_items[$i]["tax_rate"];
				}
				$order_data["subtotal_amount"] = $order_data["subtotal_amount"] + $order_items[$i]["admin_price"] * $order_items[$i]["admin_quantity"];
			}
		}
		$db->query("
			SELECT
				".DB_PREFIX."users.*,
				billing_countries.name AS country_name
			FROM ".DB_PREFIX."users
			LEFT JOIN ".DB_PREFIX."countries AS billing_countries ON ".DB_PREFIX."users.country = billing_countries.coid
			WHERE uid='".intval($order_data["uid"])."'"
		);
		if($db->moveNext()){
			$user_data = $db->col;
			view()->assign("EmailTitle", "Order Completed");

			$order_data["shipping_tracking"] = $order_data["shipping_tracking"] != "" ? unserialize($order_data["shipping_tracking"]) : false;

			view()->assign("order_data", $order_data);
			view()->assign("order_items", $order_items);
			view()->assign("user_data", $user_data);

			// credit to ...zone members
			require_once("content/classes/class.currencies.php");
			$currencies = new Currencies($db);
			$currencies->getCurrentCurrency();
			if (!isset($_SESSION['default_currency']))
			{
			    $_SESSION['default_currency'] = $currencies->getDefaultCurrency();
			}

			$message_user = view()->fetch("templates/emails/order_completed_".$user_data["email_mode"].".html");
			send_mail($user_data["email"], stripslashes($settings["CompanyName"].": ".$msg["email"]["subject_order_completed"]." - ".$order_data["order_num"]), $message_user, "", $user_data["email_mode"]);
		}
	}
	return true;
}

/**
 * Send email to a friend
 * @param $db
 * @param $yname
 * @param $yemail
 * @param $fname
 * @param $femail
 * @param $pid
 * @param $msg
 */
function emailToFriend(&$db, $yname, $yemail, $fname, $femail, $pid, $msg){
	global $settings;
	global $msg;
	global $order;
	if($settings["CatalogEmailToFriend"] == "Disabled"){
		return false;
	}
	require_once("content/classes/class.products.php");
	$_products = new ShoppingCartProducts($db, $settings);
	$_products->taxRates = $order->taxRates;
	$_product = $_products->getProductById($pid, 0);

	view()->assign("EmailTitle", $msg["email"]["title_to_friend"]);
	view()->assign("product", $_product);
	view()->assign("user_name", $yname);
	view()->assign("user_email", $yemail);
	view()->assign("friend_name", $fname);
	view()->assign("friend_email", $femail);

	if( !ini_get('safe_mode') )
		set_time_limit(300);

	if($settings["CatalogEmailToFriend"] == "HTML"){
		//send HTML email
		$message_html = view()->fetch("templates/emails/to_friend_html.html");
		send_mail($femail, sprintf($msg["email"]["subject_to_friend"], $fname, $yname), $message_html, array('name'=>stripslashes($yname),'email'=>$yemail), "html");
	}
	if($settings["CatalogEmailToFriend"] == "Text"){
		//send TEXT email
		$message_text = view()->fetch("templates/emails/to_friend_text.html");
		send_mail($femail, sprintf($msg["email"]["subject_to_friend"], $fname, $yname), $message_text, array('name'=>stripslashes($yname),'email'=>$yemail), "text");
	}
}

/**
 * Email wishlist
 * @param $db
 * @param $mail_subject
 * @param $your_email
 * @param $uid
 * @param $wishlist
 */
function emailWishlist(&$db, $mail_subject, $your_email, $uid, $wishlist)
{
	global $settings;

	$db->query("
		SELECT fname, lname, email_mode
		FROM ".DB_PREFIX."users
		WHERE uid='".intval($uid)."'
	");

	if ($user = $db->moveNext())
	{
		view()->assign("fname", $user["fname"]);
		view()->assign("lname", $user["lname"]);
		view()->assign("EmailTitle", $mail_subject);
		view()->assign("wishlist", $wishlist);
		view()->assign("GlobalHttpUrl", $settings["GlobalHttpUrl"]);

		//assign smarty vars
		view()->assign("products", $wishlist);
		view()->assign("products_file", strtolower("catalog_thumb1.html"));

		if (!ini_get('safe_mode')) set_time_limit(300);

		if ($user["email_mode"] == "html")
		{
			//send HTML email
			$message_html = view()->fetch("templates/emails/wishlist_html.html");
			send_mail($your_email, sprintf($mail_subject, $user["fname"], $user["lname"]), $message_html, "", "html");
		}

		if ($user["email_mode"]  == "text")
		{
			//send TEXT email
			$message_text = view()->fetch("templates/emails/email_wishlist_text.html");
			send_mail($your_email, $settings["CompanyName"].": ".sprintf($mail_subject, $user["fname"], $user["lname"]), $message_text, "", "text");
		}
	}
}

/**
 * Email to customer?
 * @param $db
 * @param $oid
 * @param $order_num
 * @param $emailid
 * @param $message_html
 * @param $sub
 */
function emailToCustomer(&$db, $oid, $order_num, $emailid, $message_html, $sub){
	global $settings;

	if( !ini_get('safe_mode') )
		set_time_limit(300);

	//send HTML email
	$message_html = "Order Id: ".$order_num."<br /><br /><br />".$message_html."<br /><br /><br />".
	send_mail($emailid, $settings["CompanyName"].": ".sprintf($sub), $message_html, "", "html");
}

/**
 * EMail notification of drop ship products
 * @param $db
 * @param $oid
 */
function emailProductsLocationsNotify(&$db, $orderId)
{
	global $settings;
	global $msg;

	if (isset($settings['ProductsLocationsSendOption']) && $settings['ProductsLocationsSendOption'] == 'Off')
		return;

	//get order data
	$order = $db->selectOne("
		SELECT
			orders.*,
			countries.name AS shipping_country_name,
			states.name AS shipping_state_name
		FROM ".DB_PREFIX."orders AS orders
		LEFT JOIN ".DB_PREFIX."countries AS countries ON orders.shipping_country = countries.coid
		LEFT JOIN ".DB_PREFIX."states AS states ON orders.shipping_state = states.stid
		WHERE orders.oid='".intval($orderId)."'
	");

	//get order content and locations
	$items = $db->selectAll("
		SELECT
			orders_content.title,
			orders_content.product_id,
			orders_content.product_sub_id,
			orders_content.product_upc,
			orders_content.product_gtin,
			orders_content.product_mpn,
			orders_content.admin_quantity,
			orders_content.options,
			products_locations.*
		FROM ".DB_PREFIX."orders_content AS orders_content
		INNER JOIN ".DB_PREFIX."products_locations AS products_locations
			ON products_locations.products_location_id = orders_content.products_location_id
		LEFT JOIN ".DB_PREFIX."countries AS countries ON products_locations.country = countries.coid
		LEFT JOIN ".DB_PREFIX."states AS states ON products_locations.state = states.stid
		WHERE
			orders_content.oid='".intval($orderId)."'
		ORDER BY
			products_locations.products_location_id,
			orders_content.title

	");

	$locations = array();
	$locationsItems = array();

	foreach ($items as $item)
	{
		$locations[$item["products_location_id"]] = $item;

		if (array_key_exists($item["products_location_id"], $locationsItems))
		{
			$locationsItems[$item["products_location_id"]][] = $item;
		}
		else
		{
			$locationsItems[$item["products_location_id"]] = array($item);
		}
	}

	view()->assign("order", $order);
	foreach ($locations as $location)
	{
		view()->assign("location", $location);
		view()->assign("items", $locationsItems[$location["products_location_id"]]);
		$email = view()->fetch("templates/emails/products_location_notification_".$location["email_type"].".html");
		send_mail($location["notify_email"], $settings["GlobalSiteName"].": ".$msg["email"]["new_shipment_notification"], $email, "", $location["email_type"]);

	}
}

/**
 * Send order received email
 * @param $db
 * @param $order
 * @param $user
 */
function emailCartAbandoned($db, $orderRow, $orderItemRows, $userRow, $wrappingContent, $subject)
{
	global $settings;
	global $msg;

	view()->assign("user_data", $userRow);
	view()->assign("order_items", $orderItemRows);

	if ($userRow["email_mode"]=="html")
	{
		$itemsInCartContent = view()->fetch("templates/emails/drift_email_abandoned_cart_contents_html.html");
	}
	else
	{
		$itemsInCartContent = view()->fetch("templates/emails/drift_email_abandoned_cart_contents_text.html");
	}
	$message = $wrappingContent;
	$message = str_replace("{\$ItemsInCart}", $itemsInCartContent, $message);
	$message = str_replace("{\$CartLink}", $settings["GlobalHttpUrl"] . "/?oa=RestoreCart&id=".$orderRow["security_id"], $message);
	$mailResults = send_mail($userRow["email"], $subject, $message, "", $userRow["email_mode"]);
}
