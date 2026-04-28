from odoo import fields, models, tools


class AccountInvoiceMarginReport(models.Model):
    _name = 'account.invoice.margin.report'
    _description = 'Reporte de Margen por Factura'
    _auto = False
    _order = 'invoice_date desc, id'

    move_line_id = fields.Many2one('account.move.line', string='Línea de Factura', readonly=True)
    move_id = fields.Many2one('account.move', string='Factura', readonly=True)
    invoice_name = fields.Char(string='Número de Factura', readonly=True)
    invoice_date = fields.Date(string='Fecha Factura', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_name = fields.Char(string='Descripción', readonly=True)
    quantity = fields.Float(string='Cantidad', readonly=True)
    price_unit = fields.Float(string='Precio Unitario', readonly=True)
    revenue_ars = fields.Float(string='Ingreso ARS', readonly=True, group_operator='sum')
    cost_usd = fields.Float(string='Costo USD', readonly=True, group_operator='sum')
    exchange_rate = fields.Float(string='Tipo de Cambio', readonly=True, group_operator='avg')
    cost_ars = fields.Float(string='Costo ARS', readonly=True, group_operator='sum')
    margin_ars = fields.Float(string='Ganancia ARS', readonly=True, group_operator='sum')
    margin_percent = fields.Float(string='Margen %', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    aml.id AS id,
                    aml.id AS move_line_id,
                    am.id AS move_id,
                    am.name AS invoice_name,
                    am.invoice_date AS invoice_date,
                    aml.partner_id AS partner_id,
                    aml.product_id AS product_id,
                    aml.name AS product_name,
                    aml.quantity AS quantity,
                    aml.price_unit AS price_unit,
                    ABS(aml.amount_currency) AS revenue_ars,
                    COALESCE(pt.standard_price, 0.0) * ABS(aml.quantity) AS cost_usd,
                    COALESCE(am.invoice_currency_rate, 1.0) AS exchange_rate,
                    (COALESCE(pt.standard_price, 0.0) * ABS(aml.quantity)) * COALESCE(am.invoice_currency_rate, 1.0) AS cost_ars,
                    ABS(aml.amount_currency) - ((COALESCE(pt.standard_price, 0.0) * ABS(aml.quantity)) * COALESCE(am.invoice_currency_rate, 1.0)) AS margin_ars,
                    CASE
                        WHEN ABS(aml.amount_currency) > 0
                        THEN (ABS(aml.amount_currency) - ((COALESCE(pt.standard_price, 0.0) * ABS(aml.quantity)) * COALESCE(am.invoice_currency_rate, 1.0))) / ABS(aml.amount_currency)
                        ELSE 0.0
                    END AS margin_percent
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                LEFT JOIN product_product pp ON pp.id = aml.product_id
                LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                WHERE am.move_type IN ('out_invoice', 'out_refund')
                  AND aml.display_type = 'product'
            )
        """ % (self._table,))
