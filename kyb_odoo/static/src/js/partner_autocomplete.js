odoo.define('kyb_odoo.partner_autocomplete', function (require) {
'use strict';

var PartnerAutocompleteMixin = require('partner.autocomplete.Mixin');
var FieldAutocomplete = require('partner.autocomplete.fieldchar');
var PartnerMany2One = require('partner.autocomplete.many2one');

// 1. Law 25-11 Sovereign Compliance: Disable external outbound browser calls
// and prevent foreign domain URLs from polluting the autocomplete dropdown.
PartnerAutocompleteMixin._getClearbitSuggestions = function () {
    return Promise.resolve([]);
};

// 2. Preserve rich KYB subtitle (RC: ... · Wilaya · Forme) in suggestion.description
// instead of Odoo 14/15 overwriting it with `VAT (Country)`.
PartnerAutocompleteMixin._getOdooSuggestions = function (value, isVAT) {
    var method = isVAT ? 'read_by_vat' : 'autocomplete';
    var def = this._rpc({
        model: 'res.partner',
        method: method,
        args: [value],
    }, {
        shadow: true,
    }).then(function (suggestions) {
        return (suggestions || []).map(function (suggestion) {
            suggestion.logo = suggestion.logo || '/base/static/img/company_image.png';
            suggestion.label = suggestion.legal_name || suggestion.name;
            if (suggestion.city && suggestion.city.indexOf('RC:') !== -1) {
                suggestion.description = suggestion.city;
            } else if (!suggestion.description) {
                if (suggestion.vat) {
                    suggestion.description = suggestion.vat;
                } else if (suggestion.website) {
                    suggestion.description = suggestion.website;
                }
                if (suggestion.country_id && suggestion.country_id.display_name) {
                    if (suggestion.description) {
                        suggestion.description += ' (' + suggestion.country_id.display_name + ')';
                    } else {
                        suggestion.description = suggestion.country_id.display_name;
                    }
                }
            }
            return suggestion;
        });
    });
    return this._dropPreviousOdoo.add(def);
};

// Apply Mixin patches directly to already-extended widget prototypes (Odoo 14/15 Class.extend copies Mixin properties at definition time)
FieldAutocomplete.include({
    _getClearbitSuggestions: PartnerAutocompleteMixin._getClearbitSuggestions,
    _getOdooSuggestions: PartnerAutocompleteMixin._getOdooSuggestions,

    // Allow sovereign CNRC/DGI autocomplete on BOTH Individual (Personne Physique Cat A/C)
    // and Company (Personne Morale Cat B) records, as well as existing records.
    _isActive: function () {
        return this.model === 'res.company' || this.model === 'res.partner';
    },

    // 3. Auto-persist newly enriched partner records on selection so the Chatter
    // immediately displays the Administrator KYB Verification card (matching Odoo 17-20).
    _selectCompany: function (company) {
        var self = this;
        this._getCreateData(company).then(function (data) {
            if (data.logo) {
                var logoField = self.model === 'res.partner' ? 'image_1920' : 'logo';
                data.company[logoField] = data.logo;
            }
            if (self.model === 'res.company') {
                var fields = 'comment,child_ids,bank_ids,additional_info'.split(',');
                fields.forEach(function (field) {
                    delete data.company[field];
                });
            }
            self._setOne2ManyField('bank_ids', data.company.bank_ids);
            delete data.company.bank_ids;

            self.trigger_up('field_changed', {
                dataPointID: self.dataPointID,
                changes: data.company,
                onSuccess: function () {
                    if (self.onlyVAT) {
                        self.$input.val(self._formatValue(company.vat));
                    } else {
                        self.$input.val(self._formatValue(company.name));
                    }
                    // Auto-save the record on the main partner form so PostgreSQL
                    // assigns res_id and the Chatter immediately renders the KYB Verification card.
                    if (self.model === 'res.partner') {
                        var parentWidget = self.getParent && self.getParent();
                        var controller = parentWidget && parentWidget.getParent && parentWidget.getParent();
                        if (controller && typeof controller.saveRecord === 'function' && !controller._isFromFormViewDialog) {
                            setTimeout(function () {
                                var res = controller.saveRecord(controller.handle || self.dataPointID, { stayInEdit: false, reload: true });
                                if (res && typeof res.then === 'function') {
                                    res.then(function () {
                                        if (typeof controller.reload === 'function') {
                                            controller.reload();
                                        }
                                    });
                                }
                            }, 300);
                        }
                    }
                },
            });
        });
        this._removeDropdown();
    },
});

if (PartnerMany2One && typeof PartnerMany2One.include === 'function') {
    PartnerMany2One.include({
        _getClearbitSuggestions: PartnerAutocompleteMixin._getClearbitSuggestions,
        _getOdooSuggestions: PartnerAutocompleteMixin._getOdooSuggestions,
    });
}

});
