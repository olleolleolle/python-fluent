from __future__ import absolute_import, unicode_literals

import babel
import babel.numbers
import babel.plural

from fluent.syntax import FluentParser
from fluent.syntax.ast import Message, Term

from .builtins import BUILTINS
from .resolver import resolve
from .utils import ATTRIBUTE_SEPARATOR, TERM_SIGIL, add_message_and_attrs_to_store, ast_to_id


class FluentBundle(object):
    """
    Message contexts are single-language stores of translations.  They are
    responsible for parsing translation resources in the Fluent syntax and can
    format translation units (entities) to strings.

    Always use `FluentBundle.format` to retrieve translation units from
    a context.  Translations can contain references to other entities or
    external arguments, conditional logic in form of select expressions, traits
    which describe their grammatical features, and can use Fluent builtins.
    See the documentation of the Fluent syntax for more information.
    """

    def __init__(self, locales, functions=None, use_isolating=True):
        self.locales = locales
        _functions = BUILTINS.copy()
        if functions:
            _functions.update(functions)
        self._functions = _functions
        self._use_isolating = use_isolating
        self._messages_and_terms = {}
        self._babel_locale = self._get_babel_locale()
        self._plural_form = babel.plural.to_python(self._babel_locale.plural_form)

    def add_messages(self, source):
        parser = FluentParser()
        resource = parser.parse(source)
        # TODO - warn/error about duplicates
        for item in resource.body:
            if isinstance(item, (Message, Term)):
                full_id = ast_to_id(item)
                if full_id not in self._messages_and_terms:
                    # We add attributes to the store to enable faster looker
                    # later, and more direct code in some instances.
                    add_message_and_attrs_to_store(self._messages_and_terms, full_id, item)

    def has_message(self, message_id):
        if message_id.startswith(TERM_SIGIL) or ATTRIBUTE_SEPARATOR in message_id:
            return False
        return message_id in self._messages_and_terms

    def format(self, message_id, args=None):
        if message_id.startswith(TERM_SIGIL):
            raise LookupError(message_id)
        message = self._messages_and_terms[message_id]
        if args is None:
            args = {}
        return resolve(self, message, args)

    def _get_babel_locale(self):
        for l in self.locales:
            try:
                return babel.Locale.parse(l.replace('-', '_'))
            except babel.UnknownLocaleError:
                continue
        # TODO - log error
        return babel.Locale.default()
