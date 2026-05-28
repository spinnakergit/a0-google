from helpers.tool import Tool, Response


class ContactsSearch(Tool):
    """Search Google Contacts by name, email, or phone number."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("contacts", self.agent):
            return Response(
                message="Contacts service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.contacts_client import ContactsClient, format_contact_list

        query = self.args.get("query", "")
        limit = int(self.args.get("limit", "20"))

        if not query:
            return Response(
                message="Error: query is required. Provide a name, email, or phone number to search for.",
                break_loop=False,
            )

        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100

        client = ContactsClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Contacts unavailable. {ContactsClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            self.set_progress(f"Searching contacts for '{query}'...")

            contacts = client.search_contacts(query=query, max_results=limit)

            if not contacts:
                return Response(
                    message=f"No contacts found matching '{query}'.",
                    break_loop=False,
                )

            header = f"Found {len(contacts)} contact(s) matching '{query}':"
            result = format_contact_list(contacts)
            return Response(message=f"{header}\n\n{result}", break_loop=False)

        except Exception as e:
            return Response(
                message=f"Error searching contacts: {e}",
                break_loop=False,
            )
