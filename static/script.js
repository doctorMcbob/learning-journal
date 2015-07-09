$(function() {
    $(".hide_this").hide();

    $("#edit").on("click", function(event){
        event.preventDefault();

        var id = $("#entry-id").val();

        $.ajax({
            method: "GET",
            url: "/edit/" + id
        }).done(function(response){
            //$("#the_entry").hide()
            $("#edit_container").show();
            $("#new-title").val(response.title);
            $("#new-text").val(response.text);
        }).fail(function(){
            alert("Something went wrong :c");
        });
    });

    $("submit").on("click", function(event){
        event.preventDefault();

        var id = $("#entry-id");
        var title = $("#new-title");
        var text = $("#new-text");

        $.ajax({
            method : "POST",
            url : "/edit_entry/" + id,
            data: {
                id: id,
                title: title,
                text: text
            }
        }).done(function(response) {
            //$(".journal-entry").show();
            $("#new-title").html(response.title);
            $("#new-text").html(response.text);
            $("#edit-form-container").hide();
        }).fail(function() {
            alert("Something went wrong :c");
        });
    });
    $("cancel").on("click", function(){
        $("edit-form-container").hide();
    })
});