from helpers.tool import Tool, Response


class ContactsCreate(Tool):
    """Create a new Google Contact."""

    async def execute(self, **kwargs) -> Response:
        from usr.plugins.google.helpers.google_auth import is_service_enabled
        if not is_service_enabled("contacts", self.agent):
            return Response(
                message="Contacts service is disabled. Enable it in Google Suite plugin settings.",
                break_loop=False,
            )

        from usr.plugins.google.helpers.contacts_client import ContactsClient, format_contact

        first_name = self.args.get("first_name", "")
        last_name = self.args.get("last_name", "")
        email = self.args.get("email", "")
        phone = self.args.get("phone", "")
        organization = self.args.get("organization", "")
        title = self.args.get("title", "")

        if not first_name:
            return Response(
                message="Error: first_name is required. Provide at least a first name for the contact.",
                break_loop=False,
            )

        client = ContactsClient.from_config(agent=self.agent)
        if not client:
            return Response(
                message=f"Error: Google Contacts unavailable. {ContactsClient.last_error or 'Unknown error.'}",
                break_loop=False,
            )

        try:
            display_name = f"{first_name} {last_name}".strip()
            self.set_progress(f"Creating contact '{display_name}'...")

            result = client.create_contact(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                organization=organization,
                title=title,
            )

            contact_info = format_contact(result)
            return Response(
                message=f"Contact created successfully.\n\n{contact_info}",
                break_loop=True,
            )

        except Exception as e:
            return Response(
                message=f"Error creating contact: {e}",
                break_loop=False,
            )
