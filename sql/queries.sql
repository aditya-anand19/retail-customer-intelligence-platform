SELECT * FROM transactions LIMIT 10;

SELECT
COUNT(*) AS total_rows,
COUNT(DISTINCT customer_id) AS customers,
COUNT(DISTINCT stock_code) AS products,
COUNT(DISTINCT invoice) AS invoices
FROM transactions;

SELECT t.invoice, t.invoice_date, t.line_revenue
FROM transactions t
JOIN customers c ON t.customer_id = c.customer_id
WHERE c.country = 'United Kingdom'
AND t.invoice_date BETWEEN '2011-01-01' AND '2011-03-31'
AND t.is_cancellation = FALSE
ORDER BY t.invoice_date;

SELECT invoice, customer_id, line_revenue
FROM transactions
WHERE invoice LIKE 'C%'
ORDER BY invoice;

SELECT c.country, ROUND(SUM(t.line_revenue)::NUMERIC, 2) AS revenue
FROM transactions t
JOIN customers c ON t.customer_id = c.customer_id
WHERE t.is_cancellation = FALSE
GROUP BY c.country
ORDER BY revenue DESC
LIMIT 10;

SELECT p.description,
ROUND(SUM(t.line_revenue)::NUMERIC, 2) AS revenue,
SUM(t.quantity) AS units_sold
FROM transactions t
JOIN products p ON t.stock_code = p.stock_code
WHERE t.is_cancellation = FALSE
GROUP BY p.description
ORDER BY revenue DESC
LIMIT 10;

SELECT DATE_TRUNC('month', invoice_date) AS month,
ROUND(SUM(line_revenue)::NUMERIC, 2) AS revenue,
COUNT(DISTINCT invoice) AS orders,
ROUND((SUM(line_revenue)/COUNT(DISTINCT invoice))::NUMERIC, 2) AS avg_order_value
FROM transactions
WHERE is_cancellation = FALSE
GROUP BY 1
ORDER BY 1;

SELECT t.invoice, c.country, p.description,
t.quantity, t.line_revenue
FROM transactions t
JOIN customers c ON t.customer_id = c.customer_id
JOIN products p ON t.stock_code = p.stock_code
WHERE t.is_cancellation = FALSE
LIMIT 20;

SELECT t.customer_id, c.country,
ROUND(SUM(t.line_revenue)::NUMERIC, 2) AS total_spend,
COUNT(DISTINCT t.invoice) AS orders
FROM transactions t
JOIN customers c ON t.customer_id = c.customer_id
WHERE t.is_cancellation = FALSE
GROUP BY t.customer_id, c.country
ORDER BY total_spend DESC
LIMIT 10;

SELECT p.description,
SUM(t.quantity) AS units,
ROUND(SUM(t.line_revenue)::NUMERIC, 2) AS spend
FROM transactions t
JOIN products p ON t.stock_code = p.stock_code
WHERE t.customer_id = 17850
AND t.is_cancellation = FALSE
GROUP BY p.description
ORDER BY spend DESC;

SELECT customer_id, SUM(line_revenue) AS total_spend
FROM transactions
WHERE is_cancellation = FALSE AND customer_id IS NOT NULL
GROUP BY customer_id
HAVING SUM(line_revenue) > (
SELECT AVG(cust_total) FROM (
SELECT SUM(line_revenue) AS cust_total
FROM transactions WHERE is_cancellation = FALSE
GROUP BY customer_id
) s
)
ORDER BY total_spend DESC;

SELECT t.customer_id, t.invoice,
ROUND(SUM(t.line_revenue)::NUMERIC,2) AS order_value
FROM transactions t
WHERE t.is_cancellation = FALSE
GROUP BY t.customer_id, t.invoice
HAVING SUM(t.line_revenue) > (
SELECT AVG(order_total)
FROM (
SELECT SUM(line_revenue) AS order_total
FROM transactions x
WHERE x.customer_id = t.customer_id
AND is_cancellation = FALSE
GROUP BY invoice
) a
);

WITH monthly AS (
SELECT DATE_TRUNC('month', invoice_date) AS month,
SUM(line_revenue) AS revenue
FROM transactions
WHERE is_cancellation = FALSE
GROUP BY 1
)
SELECT month, revenue,
SUM(revenue) OVER (ORDER BY month) AS running_total,
ROUND(100.0*(revenue - LAG(revenue) OVER (ORDER BY month))
/ NULLIF(LAG(revenue) OVER (ORDER BY month),0), 1) AS mom_growth_pct
FROM monthly
ORDER BY month;

SELECT customer_id,
ROUND(SUM(line_revenue)::NUMERIC,2) AS spend,
RANK() OVER (ORDER BY SUM(line_revenue) DESC) AS spend_rank,
NTILE(10) OVER (ORDER BY SUM(line_revenue) DESC) AS decile
FROM transactions
WHERE is_cancellation = FALSE AND customer_id IS NOT NULL
GROUP BY customer_id;

WITH base AS (
SELECT customer_id,
(SELECT MAX(invoice_date) FROM transactions)::date
- MAX(invoice_date)::date AS recency_days,
COUNT(DISTINCT invoice) AS frequency,
ROUND(SUM(line_revenue)::NUMERIC,2) AS monetary
FROM transactions
WHERE is_cancellation = FALSE AND customer_id IS NOT NULL
GROUP BY customer_id
)
SELECT customer_id, recency_days, frequency, monetary,
6 - NTILE(5) OVER (ORDER BY recency_days) AS r_score,
NTILE(5) OVER (ORDER BY frequency) AS f_score,
NTILE(5) OVER (ORDER BY monetary) AS m_score
FROM base;

WITH orders AS (
SELECT DISTINCT customer_id, invoice,
invoice_date::date AS d
FROM transactions
WHERE is_cancellation = FALSE AND customer_id IS NOT NULL
),
gaps AS (
SELECT customer_id,
d - LAG(d) OVER (PARTITION BY customer_id ORDER BY d) AS gap
FROM orders
)
SELECT customer_id,
ROUND(AVG(gap),1) AS avg_days_between
FROM gaps
WHERE gap IS NOT NULL
GROUP BY customer_id
ORDER BY avg_days_between;

WITH rfm AS (
SELECT customer_id,
6 - NTILE(5) OVER (ORDER BY
(SELECT MAX(invoice_date) FROM transactions)::date
- MAX(invoice_date)::date) AS r,
NTILE(5) OVER (ORDER BY COUNT(DISTINCT invoice)) AS f,
NTILE(5) OVER (ORDER BY SUM(line_revenue)) AS m
FROM transactions
WHERE is_cancellation = FALSE AND customer_id IS NOT NULL
GROUP BY customer_id
)
SELECT customer_id, r, f, m,
CASE
WHEN r>=4 AND f>=4 THEN 'Champion'
WHEN r>=3 AND f>=3 THEN 'Loyal'
WHEN r>=4 AND f<=2 THEN 'New / Promising'
WHEN r<=2 AND f>=3 THEN 'At Risk'
ELSE 'Needs Attention'
END AS segment
FROM rfm;

WITH first_order AS (
SELECT customer_id, MIN(invoice_date) AS first_dt
FROM transactions WHERE customer_id IS NOT NULL
GROUP BY customer_id
)
SELECT DATE_TRUNC('month', t.invoice_date) AS month,
COUNT(DISTINCT CASE
WHEN DATE_TRUNC('month',t.invoice_date)
= DATE_TRUNC('month',f.first_dt)
THEN t.customer_id END) AS new_customers,
COUNT(DISTINCT CASE
WHEN DATE_TRUNC('month',t.invoice_date)
> DATE_TRUNC('month',f.first_dt)
THEN t.customer_id END) AS returning_customers
FROM transactions t
JOIN first_order f ON t.customer_id = f.customer_id
WHERE t.is_cancellation = FALSE
GROUP BY 1 ORDER BY 1;

WITH cust AS (
SELECT customer_id, SUM(line_revenue) AS rev
FROM transactions
WHERE is_cancellation = FALSE AND customer_id IS NOT NULL
GROUP BY customer_id
)
SELECT customer_id, ROUND(rev::NUMERIC,2) AS revenue,
ROUND(100.0 * SUM(rev) OVER (ORDER BY rev DESC)
/ SUM(rev) OVER (), 2) AS cumulative_pct_revenue,
ROUND(100.0 * ROW_NUMBER() OVER (ORDER BY rev DESC)
/ COUNT(*) OVER (), 2) AS cumulative_pct_customers
FROM cust ORDER BY rev DESC;

SELECT customer_id,
MAX(invoice_date)::date AS last_purchase,
(SELECT MAX(invoice_date) FROM transactions)::date
- MAX(invoice_date)::date AS days_inactive
FROM transactions
WHERE is_cancellation = FALSE AND customer_id IS NOT NULL
GROUP BY customer_id
HAVING (SELECT MAX(invoice_date) FROM transactions)::date
- MAX(invoice_date)::date > 90
ORDER BY days_inactive DESC;
