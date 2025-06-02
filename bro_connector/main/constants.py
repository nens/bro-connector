
class RegistrationLog:

    class ValidationStatus:
        VALID = "VALIDE"
        INVALID = "NIET_VALIDE"

    class DeliveryStatus:
        DELIVERED = "AANGELEVERD"
        ADDED = "OPGENOMEN_LVBRO"
        FAILED = "..."

    class ProcessStatus:
        GENERATE_SUCCESS = "succesfully_generated_startregistration_request"
        GENERATE_FAIL = "failed_to_generate_source_documents"
        VALIDATE_SUCCESS = "source_document_validation_succeeded"
        VALIDATE_FAIL = "source_document_validation_failed"
        DELIVERY_SUCCESS = "succesfully_delivered_sourcedocuments"
        DELIVERY_FAIL = "failed_to_deliver_sourcedocuments"
        CHECK_SUCCESS = "delivery_status_checked"
        CHECK_FAIL = "failed_to_check_delivery_status"

    class Action:
        REGENERATE = "Regenerate startregistration sourcedocument"
        VALIDATE = "Validate startregistration sourcedocument"
        DELIVER = "Deliver startregistration sourcedocument"
        CHECK = "Check status of startregistration"


    class Message:
        GENERATE_SUCCESS = "Attempted startregistration sourcedocument regeneration"
        GENERATE_ERROR_INPUT = "No GMW ID or filter number provided"
        GENERATE_ERROR = "Can't generate startregistration sourcedocuments for an existing registration"
        VALIDATE_SUCCESS = "Succesfully validated startregistration sourcedocument"
        VALIDATE_ERROR_GENERATE = "Can't validate a startregistration that failed to generate"
        VALIDATE_ERROR_VALIDATE = "Can't validate a document that has already been delivered"
        DELIVER_SUCCESS = "Attempted registration sourcedocument delivery"
        DELIVER_ERROR_GENERATE = "Can't deliver a startregistration that failed to generate"
        DELIVER_ERROR_ALREADY_DELIVERED = "Can't deliver a registration that has already been delivered"
        DELIVER_ERROR_NOT_VALID = "Can't deliver an invalid document or not yet validated document"
        CHECK_SUCCESS = "Attempted registration status check"
        CHECK_ERROR = "Can't check status of a delivery with no 'delivery_id'"


class AdditionLog:

    class ValidationStatus:
        PENDING = "TO_BE_VALIDATED"
        VALID = "VALIDE"
        INVALID = "NIET_VALIDE"

    class DeliveryStatus:
        DELIVERED = "AANGELEVERD"
        APPROVED = "DOORGELEVERD"
        VALIDATED = "GEVALIDEERD"
        ERROR = "404"
        FAILED = "Failed"
        FAILED_ONCE = "failed_once"
        FAILED_TWICE = "failed_twice"
        FAILED_THRICE = "failed_thrice"

    class ProcessStatus:
        GENERATE_SUCCESS = "source_document_created"
        GENERATE_FAIL = "failed_to_create_source_document"
        VALIDATE_SUCCESS = "source_document_validation_succeeded"
        VALIDATE_FAIL = "source_document_validation_failed"
        DELIVERY_SUCCESS = "source_document_delivered"
        APPROVED_SUCCESS = "delivery_approved"
        CHECK_SUCCESS = "delivery_status_checked"
        CHECK_FAIL = "failed_to_check_delivery_status"
        
    class Action:
        GENERATE = "Regenerate sourcedocuments"
        VALIDATE = "Validate sourcedocuments"
        DELIVER = "Deliver sourcedocuments"
        CHECK = "Check status delivery"

    class Message:
        GENERATE_SUCCESS = "Succesfully attempted sourcedocument regeneration"
        GENERATE_ERROR = "Can't create new sourcedocuments for an observation that has already been delivered"
        VALIDATE_SUCCESS = "Succesfully attemped document validation"
        VALIDATE_ERROR_GENERATE = "Can't validate a document that failed to generate",
        VALIDATE_ERROR_VALIDATE = "Can't revalidate document for an observation that has already been delivered"
        DELIVER_SUCCESS = "Succesfully attemped document delivery"
        DELIVER_ERROR_GENERATE = "Can't deliver a document that failed to generate"
        DELIVER_ERROR_NOT_VALID = "Can't deliver an invalid document or not yet validated document"
        DELIVER_ERROR_ALREADY_DELIVERED = "Can't deliver a registration that has already been delivered"
        CHECK_SUCCESS = "Succesfully attemped status check"
        CHECK_ERROR = "Can't check status of a delivery with no 'delivery_id'"
