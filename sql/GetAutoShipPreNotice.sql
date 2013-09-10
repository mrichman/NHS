USE [Mom-Nutri-Health]
GO

/****** Object:  StoredProcedure [dbo].[GetAutoShipPreNotice]    Script Date: 09/10/2013 13:17:00 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- ==============================================
-- Author:		Mark Richman
-- Create date: 2013-09-10
-- Description:	Get Autoship Data for EmailVision
-- ==============================================
CREATE PROCEDURE [dbo].[GetAutoShipPreNotice] 
	-- Add the parameters for the stored procedure here
	@DaysAhead int = 7
	
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

    -- DECLARE @DaysAhead int = 5
	SELECT DISTINCT 
		CUST.CUSTNUM, CLUBSUBS.ORDERNO, CLUBSUBS.NEXT_SHIP, CAST(ITEMS.QUANTO AS INT) AS QUANTO, 
		ITEMS.ITEM, STOCK.DESC1, STOCK.DESC2, CUST.FIRSTNAME, CUST.LASTNAME, CUST.EMAIL,
		'' AS SourceKey, ITEMS.IT_UNLIST, CMS.ORD_TOTAL
	FROM CLUBSUBS WITH (NOLOCK) 
		INNER JOIN CMS WITH (NOLOCK) ON CLUBSUBS.ORDERNO = CMS.ORDERNO
		INNER JOIN CUST WITH (NOLOCK) ON CLUBSUBS.BILL_CUST = CUST.CUSTNUM 
		INNER JOIN CLUBHIST WITH (NOLOCK) ON CLUBSUBS.LAST_ORDER = CLUBHIST.ORDERNO 
		INNER JOIN ITEMS WITH (NOLOCK) ON CLUBHIST.ITEM_ID = ITEMS.ITEM_ID --AND ((CLUBSUBS.TRIG_ITEM = ITEMS.ITEM) OR (CLUBSUBS.CLUB_CODE = ITEMS.ITEM))
		INNER JOIN STOCK WITH (NOLOCK) ON ITEMS.ITEM = STOCK.NUMBER
	WHERE (CLUBSUBS.NEXT_SHIP = CAST(CONVERT(varchar(8), DATEADD(d, @DaysAhead, GETDATE()), 112) AS DATETIME)) 
		AND (CLUBSUBS.STATUS = 'A') 
		AND (IT_UNLIST > 0.0000) 
		AND (ITEMS.DISCOUNT < 100) 
		AND (ITEMS.NONPRODUCT = 0)
		AND (CUST.EMAIL > '') 
		AND NOT (CUST.EMAIL LIKE '%amazon.com') 
		AND (CUST.NOEMAIL = 0) 
		--AND 
		--  ((SELECT     COUNT(CUSTNUM) AS Expr1
		--	  FROM         CONTACT
		--	  WHERE     (CUSTNUM = CUST.CUSTNUM) AND (DATED > DATEADD(D, 30 - @DaysAhead, GETDATE())) AND (EMAILSENT = 1) AND (LETCODE = 'ASPre')) = 0)
		AND ((STOCK.UNITS - STOCK.COMMITED) > 0) -- OR (CUST.CUSTNUM = 2442472)
	--UNION
	--SELECT   1745637, 777, DATEADD(DD, @DaysAhead, GETDATE()), 3, '10503', 'AtrhroZyme Plus', 'Atrhrozyme Plus is cool', 'Mark', 'Richman', 'mark.richman@nutrihealth.com',
	--				'' AS SourceKey
	ORDER BY CLUBSUBS.ORDERNO ASC, ITEM

	-- exec GetAutoShipPreNotice 15  548185
END

GO

