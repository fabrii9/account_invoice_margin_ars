from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cost_usd = fields.Float(
        string='Costo USD',
        compute='_compute_margin_fields',
        store=True,
        group_operator='sum',
    )
    exchange_rate = fields.Float(
        string='Tipo de Cambio',
        compute='_compute_exchange_rate',
        store=True,
        group_operator='avg',
    )
    revenue_ars = fields.Monetary(
        string='Ingreso ARS',
        currency_field='currency_id',
        compute='_compute_margin_fields',
        store=True,
        group_operator='sum',
    )
    cost_ars = fields.Monetary(
        string='Costo ARS',
        currency_field='currency_id',
        compute='_compute_margin_fields',
        store=True,
        group_operator='sum',
    )
    margin_ars = fields.Monetary(
        string='Ganancia ARS',
        currency_field='currency_id',
        compute='_compute_margin_fields',
        store=True,
        group_operator='sum',
    )
    margin_percent = fields.Float(
        string='Margen %',
        compute='_compute_margin_fields',
        store=True,
    )

    @api.depends('move_id.invoice_currency_rate')
    def _compute_exchange_rate(self):
        for line in self:
            line.exchange_rate = line.move_id.invoice_currency_rate or 0.0

    @api.depends(
        'product_id',
        'quantity',
        'amount_currency',
        'currency_id',
        'exchange_rate',
        'company_id',
    )
    def _compute_margin_fields(self):
        for line in self:
            # Solo calcular para líneas de producto en facturas de cliente
            if (
                not line.product_id
                or line.display_type in ('line_section', 'line_note')
                or line.move_id.move_type not in ('out_invoice', 'out_refund')
            ):
                line.cost_usd = 0.0
                line.revenue_ars = 0.0
                line.cost_ars = 0.0
                line.margin_ars = 0.0
                line.margin_percent = 0.0
                continue

            # Signo: las notas de crédito deben restar del total
            sign = -1 if line.move_id.move_type == 'out_refund' else 1

            # Costo en USD (standard_price está en USD porque la compañía es USD)
            cost_usd_unit = line.product_id.standard_price or 0.0
            cost_usd_total = cost_usd_unit * abs(line.quantity) * sign
            line.cost_usd = cost_usd_total

            # Tomamos el tipo de cambio de la factura (siempre sincronizado via related)
            invoice_rate = line.exchange_rate or 0.0

            # Fallback: si la factura no tiene tipo de cambio, buscamos en monedas
            if not invoice_rate:
                usd_currency = self.env.ref('base.USD', raise_if_not_found=False)
                ars_currency = self.env['res.currency'].search([('name', '=', 'ARS')], limit=1)
                company = line.company_id
                move_date = line.move_id.invoice_date or line.move_id.date or fields.Date.today()
                if usd_currency and ars_currency and company:
                    cost_ars = usd_currency._convert(
                        cost_usd_total,
                        ars_currency,
                        company,
                        move_date,
                    )
                else:
                    cost_ars = cost_usd_total
            else:
                # Convertimos costo USD a ARS usando el tipo de cambio de la factura
                cost_ars = cost_usd_total * invoice_rate

            line.cost_ars = cost_ars

            # Ingreso en ARS: amount_currency está en la moneda del documento (ARS)
            # Para facturas de cliente amount_currency es negativo, tomamos abs
            revenue_ars = abs(line.amount_currency) * sign if line.amount_currency else 0.0
            line.revenue_ars = revenue_ars

            if revenue_ars:
                margin = revenue_ars - cost_ars
                line.margin_ars = margin
                line.margin_percent = margin / abs(revenue_ars)  # Fracción -1 a 1 para widget percentage
            else:
                line.margin_ars = 0.0
                line.margin_percent = 0.0
