from helpers.tool import Tool, Response


class ContactsList(Tool):
    """List Google Contacts with names, emails, and phone numbers."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("contacts", self.agent):
            return Response(
                message="Contacts service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.contacts_client import ContactsClient, format_contact_list

        limit = int(self.args.get("limit", "50"))
        sort_order = self.args.get("sort_order", "LAST_NAME_ASCENDING")

        if limit < 1:
            limit = 1
        elif limit > 200:
            limit = 200

        # Validate sort_order
        valid_orders = (
            "LAST_NAME_ASCENDING",
            "FIRST_NAME_ASCENDING",
            "LAST_MODIFIED_ASCENDING",
            "LAST_MODIFIED_DESCENDING",
        )
        if sort_order not in valid_orders:
            return Response(
                message=f"Error: Invalid sort_order '{sort_order}'. "
                        f"Must be one of: {', '.join(valid_orders)}.",
                break_loop=False,
            )

        client = ContactsClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Contacts unavailable. {ContactsClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            self.set_progress("Fetching contacts...")

            contacts = client.list_contacts(
                max_results=limit,
                sort_order=sort_order,
            )

            header = f"Google Contacts ({len(contacts)}):"
            result = format_contact_list(contacts)
            if contacts:
                result = f"{header}\n\n{result}"

            return Response(message=result, break_loop=False)

        except Exception as e:
            return Response(
                message=f"Error listing contacts: {e}",
                break_loop=False,
            )
