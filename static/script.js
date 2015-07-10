$(function() {
    $(".hide_this").hide();

    $("#new").on("click", function(event){
        event.preventDefault();

        $.ajax({
            method: "GET",
            url: "/new"
        }).done(function(response){
            $("#new_container").show();
        }).fail(function(){
            alert("Something went wrong :c");
        });
    });

    $("#edit").on("click", function(event){
        event.preventDefault();

        var id = $("#entry-id").val();

        $.ajax({
            method: "GET",
            url: "/edit/" + id
        }).done(function(response){
            $("#edit_container").show();
            $("#new-title").val(response.title);
            $("#new-text").val(response.text);
        }).fail(function(){
            alert("Something went wrong :c");
        });
    });

    $("#edit_submit").on("click", function(event){
        event.preventDefault();

        var id = $("#entry-id").val();
        var title = $("#new-title").val();
        var text = $("#new-text").val();
        $.ajax({
            method : "POST",
            url : "/edit_entry/" + id,
            data: {
                id: id,
                title: title,
                text: text
            }
        }).done(function(response) {
            $("#title").html(response.title);
            $("#markdown-text").html(response.text);
            $("#edit_container").hide();
        }).fail(function() {
            alert("Something went wrong :c");
        });
    });
    $("#edit_cancel").on("click", function(event){
        event.preventDefault();
        $("#edit_container").hide();
    })
    $("#new_cancel").on("click", function(event){
        event.preventDefault();
        $("#new_container").hide();
    })
});