from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cost_usd = fields.Float(
        string='Costo USD',
        compute='_compute_margin_fields',
        store=False,
    )
    exchange_rate = fields.Float(
        string='Tipo de Cambio',
        compute='_compute_margin_fields',
        store=False,
    )
    revenue_ars = fields.Monetary(
        string='Ingreso ARS',
        currency_field='currency_id',
        compute='_compute_margin_fields',
        store=False,
    )
    cost_ars = fields.Monetary(
        string='Costo ARS',
        currency_field='currency_id',
        compute='_compute_margin_fields',
        store=False,
    )
    margin_ars = fields.Monetary(
        string='Ganancia ARS',
        currency_field='currency_id',
        compute='_compute_margin_fields',
        store=False,
    )
    margin_percent = fields.Float(
        string='Margen %',
        compute='_compute_margin_fields',
        store=False,
    )

    @api.depends(
        'product_id',
        'quantity',
        'amount_currency',
        'currency_id',
        'move_id.invoice_date',
        'move_id.date',
        'company_id',
    )
    def _compute_margin_fields(self):
        usd_currency = self.env.ref('base.USD', raise_if_not_found=False)
        ars_currency = self.env['res.currency'].search([('name', '=', 'ARS')], limit=1)

        for line in self:
            # Solo calcular para líneas de producto en facturas de cliente
            if (
                not line.product_id
                or line.display_type in ('line_section', 'line_note')
                or line.move_id.move_type not in ('out_invoice', 'out_refund')
            ):
                line.cost_usd = 0.0
                line.exchange_rate = 0.0
                line.revenue_ars = 0.0
                line.cost_ars = 0.0
                line.margin_ars = 0.0
                line.margin_percent = 0.0
                continue

            # Costo en USD (standard_price está en USD porque la compañía es USD)
            cost_usd_unit = line.product_id.standard_price or 0.0
            cost_usd_total = cost_usd_unit * abs(line.quantity)
            line.cost_usd = cost_usd_total

            # Fecha para obtener el tipo de cambio
            move_date = line.move_id.invoice_date or line.move_id.date or fields.Date.today()
            company = line.company_id

            # Convertir costo USD a ARS
            if usd_currency and ars_currency and company:
                cost_ars = usd_currency._convert(
                    cost_usd_total,
                    ars_currency,
                    company,
                    move_date,
                )
                # Calculamos el tipo de cambio usado (ARS / USD)
                if cost_usd_total:
                    line.exchange_rate = cost_ars / cost_usd_total
                else:
                    line.exchange_rate = 0.0
            else:
                cost_ars = cost_usd_total
                line.exchange_rate = 1.0

            line.cost_ars = cost_ars

            # Ingreso en ARS: amount_currency está en la moneda del documento (ARS)
            # Para facturas de cliente amount_currency es negativo, tomamos abs
            revenue_ars = abs(line.amount_currency) if line.amount_currency else 0.0
            line.revenue_ars = revenue_ars

            if revenue_ars:
                margin = revenue_ars - cost_ars
                line.margin_ars = margin
                line.margin_percent = margin / revenue_ars  # Fracción 0-1 para widget percentage
            else:
                line.margin_ars = 0.0
                line.margin_percent = 0.0
